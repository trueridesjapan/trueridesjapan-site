// Посетителей из Украины, впервые открывших главную "/", отправляем на украинскую версию /ua/.
// Остальные страны (Грузия, Армения и т.д.) видят русскую главную как раньше.
// Если человек сам выбрал язык переключателем RU/UA/EN, сайт запоминает это (cookie tr_lang) и больше не перекидывает.
// Перекидываем только с главной: ссылки на машины и статьи открываются как есть.
// Проверка без Украины: https://trueridesjapan.com/?geo=UA
export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/") {
    const cookie = request.headers.get("Cookie") || "";
    const chosen = /(?:^|;\s*)tr_lang=/.test(cookie);
    const country = url.searchParams.get("geo") || (request.cf && request.cf.country) || "";
    if (!chosen && country === "UA") {
      return new Response(null, {
        status: 302,
        headers: { Location: "/ua/" + (url.hash || ""), "Cache-Control": "no-store", "Vary": "Cookie" },
      });
    }
  }
  return context.next();
}
