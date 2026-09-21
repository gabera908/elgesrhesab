import axios, { AxiosInstance } from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/** عميل HTTP مركزي — المصادقة عبر كوكيز HttpOnly (لا تخزين في JS).
 *
 * الخادم يضبط `access_token/refresh_token` ككوكيز HttpOnly عند login/refresh،
 * والمتصفح يرسلها تلقائياً مع `withCredentials`. لا يوجد أي توكن في
 * localStorage ⇒ محمي من سرقة XSS.
 */
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
  withCredentials: true,
});

// مسارات المصادقة مُستثناة من منطق التجديد — منعاً لحلقة تجديد لا نهائية:
// فشل /auth/me على صفحة الدخول كان يُطلق refresh ثم redirect ثم reload متكرر.
const AUTH_EXEMPT_PATHS = ["/auth/login", "/auth/refresh", "/auth/logout", "/auth/me"];

let isRefreshing = false;
let isRedirecting = false;

const isAuthCall = (url?: string): boolean =>
  Boolean(url) && AUTH_EXEMPT_PATHS.some((p) => (url as string).includes(p));

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    // لا تجديد ولا تحويل لمسارات المصادقة أو الطلبات غير 401
    if (status !== 401 || !originalRequest || originalRequest._retry) {
      return Promise.reject(error);
    }
    if (isAuthCall(originalRequest.url)) {
      return Promise.reject(error);
    }
    if (isRefreshing) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // الكوكي يُرسل تلقائياً — لا body مطلوب
      await axios.post(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true });
      return api(originalRequest);
    } catch (refreshError) {
      // تحويل واحد فقط، وبدون تكرار لو نحن أصلاً على صفحة الدخول
      if (!isRedirecting && !window.location.pathname.startsWith("/login")) {
        isRedirecting = true;
        window.location.href = "/login";
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

/** توافق رجعي: دوال فارغة — لم يعد هناك توكن في التخزين المحلي. */
export function storeTokens(_access: string, _refresh: string): void {
  // قصداً لا شيء: الكوكيز تُدار من الخادم عبر Set-Cookie
}

export function clearTokens(): void {
  // قصداً لا شيء محلياً: المسح يتم عبر POST /api/auth/logout
  try {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  } catch {
    /* تجاهل */
  }
}

export default api;

