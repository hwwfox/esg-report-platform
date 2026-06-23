import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.evaluate(() => window.localStorage.clear());
});

test('redirects unauthenticated workbench users to the login page', async ({ page }) => {
  await page.goto('/workbench');

  await expect(page).toHaveURL(/.*\/login/);
  await expect(page.getByRole('heading', { name: 'ESG报告平台登录' })).toBeVisible();
});

test('renders the forbidden page', async ({ page }) => {
  await page.goto('/403');

  await expect(page.getByText('无权限')).toBeVisible();
  await expect(page.getByText('当前账号无权访问该资源，请联系管理员。')).toBeVisible();
});
