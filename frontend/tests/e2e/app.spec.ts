import { test, expect } from '@playwright/test';

test('creates a card and opens detail modal', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.card-item').first()).toBeVisible();

  const urlInput = page.getByPlaceholder('새로운 URL을 붙여넣어 지식을 저장하세요...');
  const createResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/api/cards/') && response.request().method() === 'POST' && response.status() === 201,
  );
  await urlInput.fill(`https://example.com/?e2e=${Date.now()}`);
  await page.getByRole('button', { name: '저장' }).click();
  await createResponsePromise;

  const cardTitles = page.locator('.card-item h3');
  await expect(cardTitles.first()).toBeVisible();
  await page.locator('.card-item').first().click();
  await expect(page.getByRole('link', { name: /원본 사이트 열기/i })).toBeVisible();
});
