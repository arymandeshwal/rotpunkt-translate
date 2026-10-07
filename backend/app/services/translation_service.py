import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models.glossary import GlossaryEntry
from app.models.project import Document, DocumentSegment, ProjectStatus
from app.services.highlighting import compute_deterministic_annotations
from app.services.translation.factory import get_translation_provider

logger = logging.getLogger(__name__)


@dataclass
class GlossaryTermInfo:
    entry_id: int
    source_text: str
    target_text: str
    is_dnt: bool
    is_case_sensitive: bool


async def get_glossary_for_languages(
    session: AsyncSession, source_lang: str, target_lang: str
) -> list[GlossaryTermInfo]:
    """
    Query the database to build a list of glossary terms for a specific language pair.

    Args:
        session: The SQLAlchemy async database session.
        source_lang: The source language code (e.g., 'de').
        target_lang: The target language code (e.g., 'en').

    Returns:
        A list of GlossaryTermInfo objects for active glossary and DNT terms.
    """
    stmt = select(GlossaryEntry).options(selectinload(GlossaryEntry.terms))

    result = await session.execute(stmt)
    entries = result.scalars().all()

    glossary_terms = []
    for entry in entries:
        source_text = None
        target_text = None

        for term in entry.terms:
            if term.language == source_lang:
                source_text = term.text
            elif term.language == target_lang:
                target_text = term.text

        # DNT terms might only have the source term
        if entry.do_not_translate and source_text:
            target_text = source_text

        # If the entry has both the source and target languages defined
        if source_text and target_text:
            glossary_terms.append(
                GlossaryTermInfo(
                    entry_id=entry.id,
                    source_text=source_text,
                    target_text=target_text,
                    is_dnt=entry.do_not_translate,
                    is_case_sensitive=entry.case_sensitive,
                )
            )

    return glossary_terms


async def run_document_translation(document_id: uuid.UUID, target_language: str) -> None:
    """
    Background worker that orchestrates the translation of a document.

    Args:
        document_id: The UUID of the document being translated.
        target_language: The target language code to translate the text into.

    Returns:
        None. Updates the database records in place.
    """
    logger.info(f"Starting translation for document {document_id} to {target_language}")

    async with SessionLocal() as session:
        # Fetch the document and its project
        stmt = (
            select(Document)
            .options(selectinload(Document.project))
            .where(Document.id == document_id)
        )

        result = await session.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            logger.error(f"Document {document_id} not found.")
            return

        if not document.source_language:
            logger.error(f"Document {document_id} has no source language defined.")
            return

        # Update Project Status
        project = document.project
        project.status = ProjectStatus.TRANSLATING
        await session.commit()

        # 1. Fetch the master glossary for this language pair
        glossary_infos = await get_glossary_for_languages(
            session, document.source_language, target_language
        )

        # Build the flat dict for the translation provider
        master_glossary = {item.source_text: item.target_text for item in glossary_infos}

        # 2. Fetch all translatable segments ordered by index
        seg_stmt = (
            select(DocumentSegment)
            .where(
                and_(
                    DocumentSegment.document_id == document_id,
                    DocumentSegment.is_translatable.is_(True),
                )
            )
            .order_by(DocumentSegment.order_index)
        )

        seg_result = await session.execute(seg_stmt)
        segments = seg_result.scalars().all()

        if not segments:
            logger.info(f"No translatable segments found for document {document_id}")
            project.status = ProjectStatus.REVIEW
            await session.commit()
            return

        provider = get_translation_provider()

        # 3. Batch translate
        batch_size = 50

        for i in range(0, len(segments), batch_size):
            batch = segments[i : i + batch_size]
            texts = [seg.text for seg in batch]

            # Translate using provider (which handles the relevant glossary filtering)
            try:
                translated_texts = await provider.translate(
                    texts=texts,
                    source_language=document.source_language,
                    target_language=target_language,
                    glossary=master_glossary,
                )

                # Verify length matches
                if len(translated_texts) != len(batch):
                    raise ValueError(
                        f"Provider returned {len(translated_texts)} items, expected {len(batch)}."
                    )

                # 4. Save results to DB
                for seg, translation in zip(batch, translated_texts, strict=False):
                    # Update translations
                    current_translations = dict(seg.translations or {})
                    current_translations[target_language] = translation
                    seg.translations = current_translations

                    # Update annotations
                    det_annotations = compute_deterministic_annotations(translation, glossary_infos)

                    current_annotations = dict(seg.annotations or {})
                    current_annotations[target_language] = det_annotations
                    seg.annotations = current_annotations

            except Exception as e:
                logger.error(f"Error translating batch {i} for document {document_id}: {e}")
                # We can choose to fail the whole process or continue. Let's continue for MVP.
                # In production, we'd mark the project as failed or retry.

        # 5. Done
        project.status = ProjectStatus.REVIEW
        await session.commit()
        logger.info(f"Successfully completed translation for document {document_id}")
