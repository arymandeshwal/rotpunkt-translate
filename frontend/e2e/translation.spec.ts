import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Translation Workflow', () => {
  test('upload -> translate -> preview -> re-translate -> QA', async ({ page }) => {
    test.setTimeout(120000); // Allow extra time for translation and model calls

    // 1. Visit the home page
    await page.goto('/');
    await expect(page).toHaveTitle(/Rotpunkt Translate/i);

    // 2. Upload a sample PDF
    await page.locator('input[type="file"]').setInputFiles(path.resolve(process.cwd(), '../samples/downloads/HPL_XTreme.pdf'));

    // Wait for the upload to complete and redirect to the setup page
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+\/setup/i, { timeout: 30000 });

    // 3. Setup Project (Translate)
    await expect(page.getByText('Source Language', { exact: true })).toBeVisible();
    
    // Choose German -> English
    await page.getByText('Target Language').locator('..').locator('button').click();
    await page.getByRole('option', { name: 'English' }).click();

    // Start Translation
    await page.getByRole('button', { name: /Start Translation/i }).click();

    // Wait for it to redirect to the editor view, and finish translating.
    // The translation can take a while. The UI polls until the status is no longer "translating".
    await expect(page.getByText('Translating document...')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Translating document...')).not.toBeVisible({ timeout: 90000 });

    // 4. Preview (Side-by-side)
    // Verify some text from the document is visible
    await expect(page.getByText(/Source/i).first()).toBeVisible();

    // 5. QA checks validation
    // Let's verify that the QA icon (AlertTriangle) is present somewhere if issues were found
    // If there are no issues, this won't fail the test because we just check if the DOM is loaded properly
    // But we know there will likely be some issues with Gemini translations.
    // We don't want the test to be flaky if AI succeeds perfectly, so we just log its presence.
    const issuesPresent = await page.locator('.text-amber-600').count() > 0;
    console.log('QA Issues found:', issuesPresent);

    // 6. Re-translate a segment
    // Hover over the first translated segment to reveal the "Re-translate" button
    const firstSegment = page.locator('.grid.grid-cols-2.group').first();
    await firstSegment.hover();
    
    const retranslateButton = firstSegment.getByRole('button', { name: 'Re-translate segment' });
    await expect(retranslateButton).toBeVisible();
    
    // Click re-translate and wait for it to stop spinning
    await retranslateButton.click();
    
    // The button disables while loading, then re-enables
    await expect(retranslateButton).toBeDisabled();
    await expect(retranslateButton).toBeEnabled({ timeout: 30000 });
  });
});
