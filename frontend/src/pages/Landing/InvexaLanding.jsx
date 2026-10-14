import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import transformationImg from './transformation.png';
import './InvexaLanding.css';

// Footer targets live at the top so they are easy to find and change.
const CONTACT_EMAIL = 'you@example.com';
const GITHUB_URL = 'https://github.com/your-username/invexa';

const HANDSHAKE_IMG = 'https://images.unsplash.com/photo-1638262052640-82e94d64664a?w=900&q=80&auto=format&fit=crop';
const DESK_IMG = 'https://images.unsplash.com/photo-1710488350873-392a99d1da5d?w=900&q=80&auto=format&fit=crop';

// The same logo mark is used in the navbar and the footer, so it lives in one
// place. The id prop keeps the gradient id unique when both are on the page.
function LogoMark({ id, size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="6" fill={`url(#${id})`} />
      <path d="M8 12.5L10.5 15L16 9" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <defs>
        <linearGradient id={id} x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0D9488" />
          <stop offset="1" stopColor="#2DD4BF" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// Login and Get Started appear in the desktop bar and in the mobile menu.
// One component keeps the two copies from drifting apart.
function AuthLinks({ onClick }) {
  return (
    <>
      <Link to="/role-select" className="navbar__login" onClick={onClick}>Login</Link>
      <Link to="/role-select" className="btn btn-primary" onClick={onClick}>Get Started</Link>
    </>
  );
}

// The navbar gets a frosted background after the page scrolls, so the links
// stay readable over any section. On phones the links move into a side menu.
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    // Update the scrolled flag only when the page moves past the top edge.
    function onScroll() {
      setScrolled(window.scrollY > 24);
    }
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Close the side menu after a link is tapped so the page is visible again.
  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <header className={scrolled ? 'navbar navbar--scrolled' : 'navbar'}>
      <div className="navbar__inner container">
        <Link to="/" className="navbar__logo">
          <LogoMark id="navLogoGrad" size={22} />
          Invexa
        </Link>

        <nav className={menuOpen ? 'navbar__links navbar__links--open' : 'navbar__links'}>
          <a href="#home" onClick={closeMenu}>Home</a>
          <a href="#workflow" onClick={closeMenu}>Workflow</a>
          <a href="#about" onClick={closeMenu}>About</a>
          <a href="#faq" onClick={closeMenu}>FAQ</a>
          <a href="#contact" onClick={closeMenu}>Contact</a>
          <div className="navbar__mobile-actions">
            <AuthLinks onClick={closeMenu} />
          </div>
        </nav>

        <div className="navbar__actions">
          <AuthLinks />
        </div>

        <button className={menuOpen ? 'navbar__toggle navbar__toggle--open' : 'navbar__toggle'} aria-label="Toggle menu" onClick={() => setMenuOpen(!menuOpen)}>
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </header>
  );
}

// The hero states the product in one line and shows the paper-to-digital idea
// with three photos. It is the only section that needs to work in five seconds.
function Hero() {
  return (
    <section className="hero" id="home">
      <div className="hero__card">
        <span className="hero__blob hero__blob--left" aria-hidden="true"></span>
        <span className="hero__blob hero__blob--right" aria-hidden="true"></span>

        <div className="hero__content container">
          <h1 className="hero__title">Scan. Validate. Automate.</h1>
          <p className="hero__desc">
            Invexa helps small retailers upload invoices, extract data using OCR, validate GST details,
            collaborate with their CA, and generate Tally-compatible XML files, all from one platform.
          </p>

          <span className="hero__check" aria-hidden="true">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <circle cx="20" cy="20" r="18" stroke="currentColor" strokeWidth="2" />
              <path d="M12.5 20.5L18 26l9.5-11" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>

          <div className="hero__photos">
            <div className="hero__photo hero__photo--side">
              <img src={HANDSHAKE_IMG} alt="Business partners shaking hands over a deal" />
            </div>
            <div className="hero__photo hero__photo--main">
              <img src={transformationImg} alt="Stack of paper invoices transforming into a digital laptop workflow" />
            </div>
            <div className="hero__photo hero__photo--side">
              <img src={DESK_IMG} alt="Laptop, calculator and cash on an office desk" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Four short problem cards explain why the product exists. Icons are drawn with
// currentColor so the stylesheet controls their color in one place.
const PROBLEMS = [
  {
    title: 'Manual Paperwork', desc: 'Shopkeepers spend hours every week sorting, filing and re-entering paper bills by hand.', icon: <><path d="M7 3h7l4 4v14H7z" /><path d="M10 12h5M10 16h5" /></>,
  },
  {
    title: 'Repeated CA Visits', desc: 'Retailers make frequent trips to their accountant just to submit and verify bills each month.', icon: <><path d="M4 21V9l8-5 8 5v12" /><path d="M10 21v-6h4v6" /></>,
  },
  {
    title: 'Human Errors', desc: 'Manual data entry leads to mismatched GST numbers, wrong totals and compliance headaches.', icon: <><circle cx="12" cy="12" r="9" /><path d="M12 7.5v6M12 16.5v.01" /></>,
  },
  {
    title: 'Slow Accounting', desc: 'Delayed reconciliation keeps books outdated, making real-time business decisions impossible.', icon: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  },
];

// This section names the problem before showing the solution, which is what a
// visiting retailer or CA needs to see first.
function WhyInvexa() {
  return (
    <section className="why" id="about">
      <div className="container">
        <div className="landing-head">
          <span className="eyebrow">The Problem We Solve</span>
          <h2>Why Small Retailers Need Invexa</h2>
          <p>
            Bookkeeping for small retail shops is still stuck in stacks of paper, and it costs
            time, money and accuracy every single day.
          </p>
        </div>

        <div className="why__grid">
          {PROBLEMS.map((problem) => (
            <div className="why__card" key={problem.title}>
              <span className="why__icon">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  {problem.icon}
                </svg>
              </span>
              <h3>{problem.title}</h3>
              <p>{problem.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// The nine steps are a real sequence, so they are shown as one timeline.
// Short labels keep it scannable; details belong in the app, not here.
const STEPS = [
  'Register', 'Login', 'Upload', 'OCR', 'Validation',
  'CA Review', 'Approved', 'Generate XML', 'Import to Tally',
];

function Workflow() {
  return (
    <section className="workflow" id="workflow">
      <div className="container">
        <div className="landing-head landing-head--light">
          <span className="eyebrow">How It Works</span>
          <h2>One Bill, Nine Steps, Zero Paperwork</h2>
          <p>From the moment a bill lands on the counter to the moment it is posted in Tally.</p>
        </div>

        <ol className="flow">
          {STEPS.map((label, index) => (
            <li className="flow__step" key={label}>
              <span className="flow__dot">{index + 1}</span>
              <span className="flow__label">{label}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

// Answers describe what the product really does today. Keeping them honest
// avoids promises (like fixed OCR accuracy) that the CA review has to cover.
const FAQS = [
  { q: 'Does Invexa replace my Chartered Accountant?',
    a: 'No. Invexa automates the repetitive parts, such as scanning, extraction and formatting, while your CA still reviews and approves every invoice before it reaches Tally.' },
  { q: 'What file types can I upload?',
    a: 'You can upload PDF, PNG or JPG files up to 10 MB. For a paper bill, take a clear photo with your phone and upload the picture.' },
  { q: 'How accurate is the OCR extraction?',
    a: 'It depends on the bill. Clear printed invoices work best. Invexa fills in the fields it can read, and your CA checks and corrects every field before approving.' },
  { q: 'Does the XML work directly with Tally Prime?',
    a: 'Yes. Once an invoice is approved, Invexa generates XML in the format Tally Prime imports, including the ledgers it needs, so nothing has to be created by hand.' },
  { q: 'Is my data secure?',
    a: 'Passwords are stored as hashes, each CA firm sees only its own clients and bills, and access is limited by role: client, junior CA or partner.' },
  { q: 'Can more than one CA in my firm use Invexa?',
    a: 'Yes. The partner invites junior CAs with the firm invite code, and each junior sees only the clients assigned to them.' },
];

// Only one answer is open at a time so the list stays short on small screens.
function FAQ() {
  const [openIndex, setOpenIndex] = useState(0);

  // Clicking the open question closes it; clicking another one opens that one.
  function toggle(index) {
    if (openIndex === index) {
      setOpenIndex(-1);
      return;
    }
    setOpenIndex(index);
  }

  return (
    <section className="faq" id="faq">
      <div className="container">
        <div className="landing-head">
          <span className="eyebrow">FAQ</span>
          <h2>Questions, Answered</h2>
        </div>

        <div className="faq__list">
          {FAQS.map((item, index) => {
            return (
              <div className={openIndex === index ? 'faq__item faq__item--open' : 'faq__item'} key={item.q}>
                <button className="faq__question" onClick={() => toggle(index)}>
                  {item.q}
                  <span className="faq__icon">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3.5 8H12.5M8 3.5V12.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
                  </span>
                </button>
                <div className="faq__answer">
                  <p>{item.a}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// One clear closing action. There is no second button because nothing else
// on the page needs to be reached from here.
function CTA() {
  return (
    <section className="cta">
      <div className="container">
        <div className="cta__card">
          <h2>Ready to Digitize Your Accounting?</h2>
          <p>Upload a bill, review the extracted data with your CA, and get a Tally-ready file.</p>
          <Link to="/role-select" className="btn cta__btn">Get Started</Link>
        </div>
      </div>
    </section>
  );
}

// The footer only holds links that lead somewhere real: two pages, an email
// address and the project repository.
function Footer() {
  return (
    <footer className="footer" id="contact">
      <div className="container">
        <div className="footer__top">
          <div className="footer__brand">
            <Link to="/" className="footer__logo">
              <LogoMark id="footerLogoGrad" size={20} />
              Invexa
            </Link>
            <p>Automated bill digitization and Tally integration for small retailers.</p>
          </div>

          <nav className="footer__links">
            <Link to="/privacy">Privacy</Link>
            <Link to="/terms">Terms</Link>
            <a href={`mailto:${CONTACT_EMAIL}`}>Contact</a>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub</a>
          </nav>
        </div>

        <p className="footer__bottom">© {new Date().getFullYear()} Invexa. All rights reserved.</p>
      </div>
    </footer>
  );
}

// Each section is a separate component so we can reorder them or remove one
// without touching the others.
export default function Landing() {
  return (
    <div className="app">
      <Navbar />
      <main>
        <Hero />
        <WhyInvexa />
        <Workflow />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}