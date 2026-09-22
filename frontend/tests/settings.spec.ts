import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://100.84.254.18:8095';
const TEST_USER = process.env.TEST_USER || 'admin';
const TEST_PASS = process.env.TEST_PASS || 'Tmp!1234567890';

async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[id="username"]', TEST_USER);
  await page.fill('input[id="password"]', TEST_PASS);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(`${BASE_URL}/`);
}

test.describe('الإعدادات: النسخ الاحتياطي والاستعادة وإنشاء المستخدمين', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/settings`);
    await expect(page.locator('h1:has-text("الإعدادات")')).toBeVisible();
  });

  test('إنشاء نسخة احتياطية تظهر في القائمة مع زر تحميل', async ({ page }) => {
    await page.click('button:has-text("إنشاء نسخة احتياطية الآن")');
    await expect(page.locator('text=تم إنشاء نسخة احتياطية مشفَّرة')).toBeVisible({ timeout: 120000 });
    await expect(page.locator('table td.font-mono').first()).toBeVisible();
    await expect(page.locator('button[title="تحميل"]').first()).toBeVisible();
  });

  test('قسم الاستعادة: اختيار نسخة + تأكيد RESTORE ثم استعادة ناجحة', async ({ page }) => {
    // تأكد من وجود نسخة أولاً
    await page.click('button:has-text("إنشاء نسخة احتياطية الآن")');
    await expect(page.locator('text=تم إنشاء نسخة احتياطية مشفَّرة')).toBeVisible({ timeout: 120000 });

    // اختيار أول نسخة للاستعادة
    await page.click('table button:has-text("اختيار")');
    await expect(page.locator('button:has-text("محددة")')).toBeVisible();

    // زر الاستعادة معطّل قبل التأكيد
    const restoreBtn = page.locator('button:has-text("استعادة النسخة")');
    await expect(restoreBtn).toBeDisabled();

    await page.fill('input[id="restoreConfirm"]', 'RESTORE');
    await expect(restoreBtn).toBeEnabled();
    await restoreBtn.click();
    await expect(page.locator('text=تمت الاستعادة بنجاح')).toBeVisible({ timeout: 300000 });
  });

  test('الاستعادة بتأكيد خاطئ مرفوضة', async ({ page }) => {
    await page.fill('input[id="restoreConfirm"]', 'WRONG');
    await expect(page.locator('button:has-text("استعادة النسخة")')).toBeDisabled();
  });

  test('زر أضف يوزر جديد يفتح نموذجاً مع مصفوفة الصلاحيات', async ({ page }) => {
    const toggle = page.locator('button:has-text("أضف يوزر جديد")');
    await expect(toggle).toBeVisible();
    // النموذج مخفي افتراضياً
    await expect(page.locator('input[id="newUsername"]')).toHaveCount(0);

    await toggle.click();
    await expect(page.locator('input[id="newFullName"]')).toBeVisible();
    await expect(page.locator('input[id="newEmail"]')).toBeVisible();
    await expect(page.locator('input[id="newUsername"]')).toBeVisible();
    await expect(page.locator('input[id="newPassword"]')).toBeVisible();
    await expect(page.locator('select[id="newRole"]')).toBeVisible();
    // مصفوفة الصلاحيات الفردية
    await expect(page.locator('text=الصلاحيات الفردية')).toBeVisible();
    await expect(page.locator('input[type="checkbox"]').first()).toBeVisible();

    // إنشاء مستخدم ببيانات فريدة
    const stamp = Date.now().toString().slice(-6);
    await page.fill('input[id="newFullName"]', `مستخدم اختبار ${stamp}`);
    await page.fill('input[id="newEmail"]', `test${stamp}@bridge-media.org`);
    await page.fill('input[id="newUsername"]', `testuser${stamp}`);
    await page.fill('input[id="newPassword"]', 'Test@12345678');
    await page.locator('select[id="newRole"]').selectOption({ index: 1 });
    // صلاحية فردية واحدة
    await page.locator('input[type="checkbox"]').first().check();
    await page.click('button:has-text("إنشاء الحساب")');
    await expect(page.locator('text=تم إنشاء الحساب الجديد')).toBeVisible({ timeout: 30000 });
  });
});
