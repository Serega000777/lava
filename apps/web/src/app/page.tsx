const categories = [
  { icon: "↗", title: "Автомобили", text: "Проверенная история и честные карточки" },
  { icon: "◇", title: "Товары", text: "От техники до вещей для дома" },
  { icon: "✦", title: "Услуги", text: "Специалисты с репутацией и портфолио" },
];

export default function Home() {
  return (
    <main>
      <header className="nav">
        <Link className="brand" href="/" aria-label="Lava, главная">Lava<span>.</span></Link>
        <nav aria-label="Основная навигация">
          <a href="#categories">Категории</a><a href="#trust">Как это работает</a>
        </nav>
        <div className="actions"><button className="ghost">Войти</button><button>Разместить объявление</button></div>
      </header>
      <section className="hero">
        <p className="eyebrow">ЧЕСТНЫЕ ОБЪЯВЛЕНИЯ РЯДОМ</p>
        <h1>Находите нужное.<br /><em>Без лишнего шума.</em></h1>
        <p className="lead">Органическая выдача по качеству, проверенные продавцы и AI, который помогает — но не приукрашивает факты.</p>
        <form className="search" role="search">
          <label className="sr-only" htmlFor="query">Поиск объявлений</label>
          <input id="query" placeholder="Что вы ищете?" />
          <button type="submit">Найти</button>
        </form>
        <div className="proof"><span>✓ Без платного поднятия</span><span>✓ AI-контент отмечен</span><span>✓ Прозрачные правила</span></div>
      </section>
      <section className="categories" id="categories">
        <div className="section-title"><p>НАЧНИТЕ С КАТЕГОРИИ</p><h2>Всё нужное — в трёх разделах</h2></div>
        <div className="grid">{categories.map((category) => (
          <a className="card" href="#" key={category.title}>
            <span className="icon">{category.icon}</span><h3>{category.title}</h3><p>{category.text}</p><b>Смотреть объявления →</b>
          </a>
        ))}</div>
      </section>
      <section className="trust" id="trust"><p>РЕПУТАЦИЯ ВАЖНЕЕ БЮДЖЕТА</p><h2>Выше показываются не те, кто больше заплатил, а те, кому можно доверять.</h2></section>
      <footer><Link className="brand" href="/">Lava<span>.</span></Link><p>Новая культура объявлений</p><small>© 2026 Lava</small></footer>
    </main>
  );
}
import Link from "next/link";

