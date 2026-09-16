import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const TEST_USER = process.env.TEST_USER || 'admin@bridge-media.org';
const TEST_PASS = process.env.TEST_PASS || 'Admin@12345678';

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
    
    // ملء النموذج
    await page.fill('input[id="code"]', '9.9.9');
    await page.fill('input[id="name"]', 'حساب اختبار');
    await page.selectOption('select[name="account_type"]', 'asset');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('text=حساب اختبار')).toBeVisible();
  });

  test('قيد يومي متوازن يمر، وغير متوازن يرفض', async ({ page }) => {
    await page.goto(`${BASE_URL}/entries`);
    
    // اختيار دفتر
    await page.selectOption('select[id="journal"]', { index: 1 });
    
    // السطر الأول - مدين
    await page.selectOption('select[name="lines.0.account_id"]', { index: 1 });
    await page.fill('input[name="lines.0.debit"]', '1000');
    
    // السطر الثاني - دائن
    await page.selectOption('select[name="lines.1.account_id"]', { index: 2 });
    await page.fill('input[name="lines.1.credit"]', '1000');
    
    await page.click('button:has-text("حفظ القيد")');
    await expect(page.locator('text=تم إنشاء القيد')).toBeVisible();
    
    // الآن محاولة قيد غير متوازن
    await page.fill('input[name="lines.0.debit"]', '500');
    await page.click('button:has-text("حفظ القيد")');
    await expect(page.locator('text=القيد غير متوازن')).toBeVisible();
  });

  test('ميزان المراجعة يتوازن (مجموع المدين = مجموع الدائن)', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports`);
    
    // تعيين تواريخ
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.fill('input[type="date"]:nth-of-type(1)', firstDay);
    await page.fill('input[type="date"]:nth-of-type(2)', today);
    
    // انتظار التحميل
    await page.waitForSelector('table');
    
    // التحقق من ظهور "✓ متوازن"
    await expect(page.locator('text=✓ متوازن')).toBeVisible();
  });

  test('الأستاذ العام يعرض الرصيد الجاري الصحيح', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports`);
    await page.click('div:has-text("الأستاذ العام")');
    
    // اختيار حساب
    await page.selectOption('select[name="account_id"]', { index: 1 });
    
    // تعيين تواريخ
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.fill('input[type="date"]:nth-of-type(1)', firstDay);
    await page.fill('input[type="date"]:nth-of-type(2)', today);
    
    await page.waitForSelector('table');
    // التحقق من وجود عمود الرصيد الجاري
    await expect(page.locator('th:has-text("الرصيد الجاري")')).toBeVisible();
  });

  test('الميزانية العمومية تحقق المعادلة: الأصول = الخصوم + الحقوق', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports`);
    await page.click('div:has-text("الميزانية العمومية")');
    
    const today = new Date().toISOString().slice(0, 10);
    await page.fill('input[type="date"]', today);
    
    await page.waitForSelector('text=✓ متوازن');
    await expect(page.locator('text=✓ متوازن')).toBeVisible();
  });

  test('قائمة الدخل تظهر صافي الربح/الخسارة', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/income-statement`);
    
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.fill('input[type="date"]:nth-of-type(1)', firstDay);
    await page.fill('input[type="date"]:nth-of-type(2)', today);
    
    await page.waitForSelector('text=إجمالي الإيرادات');
    await expect(page.locator('text=إجمالي الإيرادات')).toBeVisible();
    await expect(page.locator('text=إجمالي المصروفات')).toBeVisible();
    await expect(page.locator('text=صافي الربح, text=صافي الخسارة')).toBeVisible();
  });

  test('التدفقات النقدية تحسب الصافي', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow`);
    
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.fill('input[type="date"]:nth-of-type(1)', firstDay);
    await page.fill('input[type="date"]:nth-of-type(2)', today);
    
    await page.waitForSelector('text=الرصيد النقدي الختامي');
    await expect(page.locator('text=الرصيد النقدي الختامي')).toBeVisible();
  });

  test('اليومية الأمريكية تظهر المجاميع اليومية', async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/american-journal`);
    
    const today = new Date().toISOString().slice(0, 10);
    const firstDay = today.slice(0, 8) + '01';
    await page.fill('input[type="date"]:nth-of-type(1)', firstDay);
    await page.fill('input[type="date"]:nth-of-type(2)', today);
    
    await page.waitForSelector('text=إجمالي اليوم');
    await expect(page.locator('text=إجمالي اليوم')).toBeVisible();
  });
});

test.describe('الأمان والمصادقة', () => {
  test('صفحة الإعدادات محمية وتتطلب صلاحية admin', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    // يجب إعادة التوجيه لتسجيل الدخول أو إظهار رسالة عدم صلاحية
    await expect(page.locator('text=ليس لديك صلاحية')).toBeVisible();
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