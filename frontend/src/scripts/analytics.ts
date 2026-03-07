// GA4 initialization
const gaId = document.querySelector<HTMLMetaElement>('meta[name="ga4-id"]')?.content;
if (gaId) {
  (window as any).dataLayer = (window as any).dataLayer || [];
  function gtag(..._args: any[]) {
    (window as any).dataLayer.push(arguments);
  }
  gtag('js', new Date());
  gtag('config', gaId);
}

// Clarity initialization
const clarityId = document.querySelector<HTMLMetaElement>('meta[name="clarity-id"]')?.content;
if (clarityId) {
  (function (c: any, l: Document, a: string, r: string, i: string) {
    c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
    const t = l.createElement(r) as HTMLScriptElement;
    t.async = true;
    t.src = 'https://www.clarity.ms/tag/' + i;
    const y = l.getElementsByTagName(r)[0];
    y.parentNode!.insertBefore(t, y);
  })(window, document, 'clarity', 'script', clarityId);
}
