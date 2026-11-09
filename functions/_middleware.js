// Язык главной "/" для нового посетителя (решение 10 ноября):
//  1) человек уже сам выбрал язык переключателем RU/UA/EN (cookie tr_lang) — ничего не трогаем;
//  2) заходит из Украины — украинская версия /ua/;
//  3) иначе по языку телефона/браузера: украинский -> /ua/, английский -> /en/, русский и все остальные -> русская главная.
// Перекидываем только с главной: ссылки на машины и статьи открываются как есть.
// Проверка: /?geo=UA (как из Украины), /?al=en (как телефон на английском).
export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/") {
    const cookie = request.headers.get("Cookie") || "";
    const ua = request.headers.get("User-Agent") || "";
    const isBot = /bot|crawl|spider|slurp|facebookexternalhit|preview/i.test(ua);  // поисковики видят главную как есть
    if (!isBot && !/(?:^|;\s*)tr_lang=/.test(cookie)) {
      const country = url.searchParams.get("geo") || (request.cf && request.cf.country) || "";
      const al = (url.searchParams.get("al") || request.headers.get("Accept-Language") || "").toLowerCase();
      const first = al.split(",")[0].trim().slice(0, 2);
      let target = null;
      if (country === "UA" || first === "uk") target = "/ua/";
      else if (first === "en") target = "/en/";
      if (target) {
        return new Response(null, {
          status: 302,
          headers: { Location: target, "Cache-Control": "no-store", "Vary": "Cookie, Accept-Language" },
        });
      }
    }
  }
  return context.next();
}
