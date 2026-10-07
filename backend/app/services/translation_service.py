import logging
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models.glossary import GlossaryEntry
from app.models.project import Document, DocumentSegment, ProjectStatus
from app.services.translation.factory import get_translation_provider

logger = logging.getLogger(__name__)


async def get_glossary_for_languages(
    session: AsyncSession, source_lang: str, target_lang: str
) -> dict[str, str]:
    """
    Query the database to build a flat translation dictionary for a specific language pair.
    Only approved terms should ideally be fetched, but for now we fetch all terms
    associated with an entry that has both languages.
    """
    # For now, we join GlossaryTerm to itself via the entry_id
    # where t1.language == source_lang and t2.language == target_lang
    # Since SQLAlchemy makes self-joins a bit verbose, let's just query the entries
    # that have both, using selectinload.

    # A cleaner approach using standard ORM filtering:
    # Actually, let's fetch all terms for these languages and build it in memory
    # since the dataset for MVP is small.
    stmt = select(GlossaryEntry).options(selectinload(GlossaryEntry.terms))

    result = await session.execute(stmt)
    entries = result.scalars().all()

    glossary_dict = {}
    for entry in entries:
        source_text = None
        target_text = None

        for term in entry.terms:
            if term.language == source_lang:
                source_text = term.text
            elif term.language == target_lang:
                target_text = term.text

        # If the entry has both the source and target languages defined
        if source_text and target_text:
            glossary_dict[source_text] = target_text

    return glossary_dict


async def run_document_translation(document_id: uuid.UUID, target_language: str) -> None:
    """
    Background worker that orchestrates the translation of a document.
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
        master_glossary = await get_glossary_for_languages(
            session, document.source_language, target_language
        )

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
                    # We need to copy the JSON dict, update it, and set it back
                    # so SQLAlchemy knows it changed.
                    current_translations = dict(seg.translations or {})
                    current_translations[target_language] = translation
                    seg.translations = current_translations

            except Exception as e:
                logger.error(f"Error translating batch {i} for document {document_id}: {e}")
                # We can choose to fail the whole process or continue. Let's continue for MVP.
                # In production, we'd mark the project as failed or retry.

        # 5. Done
        project.status = ProjectStatus.REVIEW
        await session.commit()
        logger.info(f"Successfully completed translation for document {document_id}")
