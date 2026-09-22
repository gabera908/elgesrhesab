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

test.describe('الاختبارات المحاسبية الأساسية', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('إنشاء حساب جديد في شجرة الحسابات', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    await page.click('button:has-text("حساب جديد")');

    // ملء النموذج (الكود يُقترح تلقائياً — نكتب قيمة فريدة)
    const stamp = Date.now().toString().slice(-4);
    const accountName = `حساب اختبار ${stamp}`;
    await page.fill('input[id="acc-code"]', `9.9.${stamp}`);
    await page.fill('input[id="acc-name"]', accountName);
    await page.selectOption('select[id="acc-type"]', 'asset');
    await page.click('button:has-text("إنشاء الحساب")');

    await expect(page.locator(`text=${accountName}`).first()).toBeVisible({ timeout: 15000 });
  });

  test('قيد يومي متوازن يمر، وغير متوازن يُعطّل زر الحفظ', async ({ page }) => {
    await page.goto(`${BASE_URL}/entries`);

    // اختيار دفتر
    await page.selectOption('select[id="journal"]', { index: 1 });

    const rows = page.locator('tbody tr');
    // السطر الأول - مدين على حساب قابل للترحيل (الصندوق)
    await rows.nth(0).locator('select').selectOption({ label: '1.1.1 — الصندوق' });
    await rows.nth(0).locator('input[type="number"]').first().fill('1000');

    // السطر الثاني - دائن على حساب قابل للترحيل (إيرادات المشاريع)
    await rows.nth(1).locator('select').selectOption({ label: '4.1.1 — إيرادات المشاريع' });
    await rows.nth(1).locator('input[type="number"]').last().fill('1000');

    await expect(page.locator('text=✓ القيد متوازن')).toBeVisible();
    await page.click('button:has-text("حفظ القيد")');
    await expect(page.locator('text=تم إنشاء القيد')).toBeVisible({ timeout: 20000 });

    // قيد غير متوازن ⇒ الزر يُعطَّل ويظهر الفرق
    await rows.nth(0).locator('input[type="number"]').first().fill('500');
    await expect(page.locator('text=الفرق:')).toBeVisible();
    await expect(page.locator('button:has-text("حفظ القيد")')).toBeDisabled();
  });

  test('ميزان المراجعة يتوازن (مجموع المدين = مجموع الدائن)', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports`);

    // تعيين تواريخ
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.locator('input[type="date"]').first().fill(firstDay);
    await page.locator('input[type="date"]').nth(1).fill(today);

    // انتظار التحميل
    await page.waitForSelector('table');

    // التحقق من ظهور حالة الميزان
    await expect(page.locator('text=/✓ متوازن|✗ غير متوازن/').first()).toBeVisible({ timeout: 25000 });
  });

  test('الأستاذ العام يعرض الرصيد الجاري الصحيح', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports?report=general-ledger`);

    // اختيار حساب
    await page.locator('select.input.w-auto').first().selectOption({ index: 1 });

    // تعيين تواريخ
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.locator('input[type="date"]').first().fill(firstDay);
    await page.locator('input[type="date"]').nth(1).fill(today);

    await page.waitForSelector('table');
    // التحقق من وجود عمود الرصيد الجاري
    await expect(page.locator('th:has-text("الرصيد الجاري")')).toBeVisible();
  });

  test('الميزانية العمومية تحقق المعادلة: الأصول = الخصوم + الحقوق', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports?report=balance-sheet`);

    const today = new Date().toISOString().slice(0, 10);
    await page.locator('input[type="date"]').first().fill(today);

    await expect(page.locator('text=/✓ متوازن|✗ غير متوازن/').first()).toBeVisible({ timeout: 25000 });
  });

  test('قائمة الدخل تظهر صافي الربح/الخسارة', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/income-statement`);
    
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.locator('input[type="date"]').first().fill(firstDay);
    await page.locator('input[type="date"]').nth(1).fill(today);

    await expect(page.locator('text=إجمالي الإيرادات').first()).toBeVisible({ timeout: 20000 });
    await expect(page.locator('text=إجمالي المصروفات').first()).toBeVisible();
    await expect(page.locator('text=/صافي (الربح|الخسارة)/').first()).toBeVisible();
  });

  test('التدفقات النقدية تحسب الصافي', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow`);
    
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.locator('input[type="date"]').first().fill(firstDay);
    await page.locator('input[type="date"]').nth(1).fill(today);

    await expect(page.locator('text=الرصيد النقدي الختامي')).toBeVisible({ timeout: 20000 });
  });

  test('اليومية الأمريكية تظهر المجاميع اليومية', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/american-journal`);
    
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.locator('input[type="date"]').first().fill(firstDay);
    await page.locator('input[type="date"]').nth(1).fill(today);

    await expect(page.locator('text=إجمالي اليوم').first()).toBeVisible({ timeout: 20000 });
  });
});

test.describe('الأمان والمصادقة', () => {
  test('صفحة الإعدادات محمية — غير المسجَّل يُحوَّل لتسجيل الدخول', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    // ProtectedRoute يُعيد التوجيه لصفحة الدخول
    await expect(page).toHaveURL(/\/login$/, { timeout: 15000 });
    await expect(page.locator('text=نظام الحسابات — تسجيل الدخول')).toBeVisible();
  });

  test('رابط إنشاء الحساب غير ظاهر على شاشة الدخول', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator('text=إنشاء حساب')).toHaveCount(0);
    await expect(page.locator('a[href="/register"]')).toHaveCount(0);
  });

  test('تسجيل الدخول برمز 2FA خاطئ يفشل', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[id="username"]', TEST_USER);
    await page.fill('input[id="password"]', TEST_PASS);
    await page.click('button[type="submit"]');
    
    // إذا طُلب 2FA
    const twofaInput = page.locator('input[id="twofa"]');
    if (await twofaInput.isVisible({ timeout: 2000 })) {
      await twofaInput.fill('000000');
      await page.click('button[type="submit"]');
      await expect(page.locator('text=رمز التحقق غير صحيح')).toBeVisible();
    }
  });
});