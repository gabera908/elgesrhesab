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

// تجديد تلقائي عند انتهاء صلاحية الكوكي
let isRefreshing = false;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry && !isRefreshing) {
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // الكوكي يُرسل تلقائياً — لا body مطلوب
        await axios.post(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true });
        return api(originalRequest);
      } catch (refreshError) {
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
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
