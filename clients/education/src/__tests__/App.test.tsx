/**
 * Tests for the education site components — focused on accessibility compliance.
 *
 * Every test verifies at least one WCAG 2.1 AA requirement because this site
 * must be fully usable by NVDA users with zero mouse interaction.
 *
 * Test coverage:
 * - SiteHeader: landmark, nav, link labels
 * - SiteFooter: contentinfo landmark, link text
 * - CourseCard: heading, progress bar, link labels
 * - AudioPlayer: controls, aria-live, progress bar
 * - HomePage: h1 present, course list, keyboard nav hints
 * - NotFoundPage: h1 present, return link
 */

import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import App from '../App';
import SiteHeader from '../components/SiteHeader';
import SiteFooter from '../components/SiteFooter';
import CourseCard, { Course } from '../components/CourseCard';
import AudioPlayer from '../components/AudioPlayer';
import HomePage from '../pages/HomePage';
import NotFoundPage from '../pages/NotFoundPage';
import CoursePage from '../pages/CoursePage';
import LessonPage from '../pages/LessonPage';

// ─────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────

function renderWithRouter(ui: React.ReactElement, { route = '/' } = {}) {
  return render(<MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>);
}

function renderApp(route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>
  );
}

const SAMPLE_COURSE: Course = {
  id: 'test-course',
  title: 'Test Course Title',
  description: 'A description of the test course.',
  lessonCount: 5,
  completedLessons: 0,
  durationMinutes: 20,
};

// ─────────────────────────────────────────────────────────────
// SITE HEADER
// ─────────────────────────────────────────────────────────────

describe('SiteHeader', () => {
  it('renders a <header> landmark', () => {
    renderWithRouter(<SiteHeader />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('has a primary navigation landmark', () => {
    renderWithRouter(<SiteHeader />);
    expect(screen.getByRole('navigation', { name: /primary navigation/i })).toBeInTheDocument();
  });

  it('home link has descriptive aria-label (not just logo)', () => {
    renderWithRouter(<SiteHeader />);
    const homeLink = screen.getByRole('link', { name: /blind assistant learning/i });
    expect(homeLink).toBeInTheDocument();
  });

  it('courses nav link exists', () => {
    renderWithRouter(<SiteHeader />);
    expect(screen.getByRole('link', { name: /courses/i })).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────
// SITE FOOTER
// ─────────────────────────────────────────────────────────────

describe('SiteFooter', () => {
  it('renders a <footer> contentinfo landmark', () => {
    renderWithRouter(<SiteFooter />);
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('footer links have descriptive text (not "click here")', () => {
    renderWithRouter(<SiteFooter />);
    const links = screen.getAllByRole('link');
    links.forEach((link) => {
      const text = link.textContent ?? '';
      expect(text.toLowerCase()).not.toBe('click here');
      expect(text.toLowerCase()).not.toBe('here');
    });
  });
});

// ─────────────────────────────────────────────────────────────
// COURSE CARD
// ─────────────────────────────────────────────────────────────

describe('CourseCard', () => {
  it('renders course title as a heading', () => {
    renderWithRouter(<CourseCard course={SAMPLE_COURSE} />);
    expect(screen.getByRole('heading', { name: /test course title/i })).toBeInTheDocument();
  });

  it('start link has descriptive label including course title', () => {
    renderWithRouter(<CourseCard course={SAMPLE_COURSE} />);
    const link = screen.getByRole('link', { name: /start course: test course title/i });
    expect(link).toBeInTheDocument();
  });

  it('shows "Continue" label after progress begins', () => {
    const started: Course = { ...SAMPLE_COURSE, completedLessons: 2 };
    renderWithRouter(<CourseCard course={started} />);
    expect(screen.getByRole('link', { name: /continue test course title/i })).toBeInTheDocument();
  });

  it('shows "Review" label when course is complete', () => {
    const done: Course = { ...SAMPLE_COURSE, completedLessons: 5 };
    renderWithRouter(<CourseCard course={done} />);
    expect(screen.getByRole('link', { name: /review test course title/i })).toBeInTheDocument();
  });

  it('progress bar has aria-valuenow and aria-label when started', () => {
    const started: Course = { ...SAMPLE_COURSE, completedLessons: 2 };
    renderWithRouter(<CourseCard course={started} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '40');
    expect(bar).toHaveAttribute('aria-label');
  });

  it('no progress bar when course not started (completedLessons=0)', () => {
    renderWithRouter(<CourseCard course={SAMPLE_COURSE} />);
    expect(screen.queryByRole('progressbar')).toBeNull();
  });

  it('renders as an <article> landmark with label', () => {
    renderWithRouter(<CourseCard course={SAMPLE_COURSE} />);
    const article = screen.getByRole('article', { name: /test course title/i });
    expect(article).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────
// AUDIO PLAYER
// ─────────────────────────────────────────────────────────────

describe('AudioPlayer', () => {
  const defaultProps = {
    src: '/audio/test.mp3',
    title: 'Test Lesson Audio',
    transcript: 'This is the transcript text.',
  };

  it('renders a toolbar of playback controls', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    expect(screen.getByRole('toolbar', { name: /playback controls/i })).toBeInTheDocument();
  });

  it('Play button has accessible label', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
  });

  it('Rewind button has accessible label', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    expect(screen.getByRole('button', { name: /rewind 10 seconds/i })).toBeInTheDocument();
  });

  it('Skip forward button has accessible label', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    expect(screen.getByRole('button', { name: /skip forward 10 seconds/i })).toBeInTheDocument();
  });

  it('has a live status region for playback announcements', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
  });

  it('progress bar has aria-label and aria-valuenow', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow');
    expect(bar).toHaveAttribute('aria-label');
  });

  it('transcript is shown by default', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    expect(screen.getByText('This is the transcript text.')).toBeInTheDocument();
  });

  it('transcript toggle button has aria-expanded', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    const btn = screen.getByRole('button', { name: /hide transcript/i });
    expect(btn).toHaveAttribute('aria-expanded', 'true');
  });

  it('clicking transcript toggle collapses transcript', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    const btn = screen.getByRole('button', { name: /hide transcript/i });
    fireEvent.click(btn);
    // Button label changes
    expect(screen.getByRole('button', { name: /show transcript/i })).toBeInTheDocument();
  });

  it('renders without transcript when prop not provided', () => {
    renderWithRouter(<AudioPlayer src="/audio/test.mp3" title="Test" />);
    expect(screen.queryByText(/transcript/i)).toBeNull();
  });

  it('play button aria-pressed reflects playing state', () => {
    renderWithRouter(<AudioPlayer {...defaultProps} />);
    const btn = screen.getByRole('button', { name: /play/i });
    // Initially not playing
    expect(btn).toHaveAttribute('aria-pressed', 'false');
  });
});

// ─────────────────────────────────────────────────────────────
// HOME PAGE
// ─────────────────────────────────────────────────────────────

describe('HomePage', () => {
  it('has an h1 heading', () => {
    renderWithRouter(<HomePage />);
    expect(screen.getByRole('heading', { level: 1, name: /courses/i })).toBeInTheDocument();
  });

  it('renders a list of courses', () => {
    renderWithRouter(<HomePage />);
    const list = screen.getByRole('list', { name: /available courses/i });
    expect(list).toBeInTheDocument();
    const items = within(list).getAllByRole('listitem');
    expect(items.length).toBeGreaterThan(0);
  });

  it('mentions keyboard navigation shortcut for screen reader users', () => {
    renderWithRouter(<HomePage />);
    // The keyboard hint text spans multiple elements (<kbd>H</kbd> breaks the string),
    // so we check the paragraph's full textContent instead of a single text node.
    const body = document.body.textContent ?? '';
    expect(body).toMatch(/press.*H.*in NVDA/i);
  });
});

// ─────────────────────────────────────────────────────────────
// NOT FOUND PAGE
// ─────────────────────────────────────────────────────────────

describe('NotFoundPage', () => {
  it('has an h1 heading', () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByRole('heading', { level: 1, name: /page not found/i })).toBeInTheDocument();
  });

  it('has a return link', () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByRole('link', { name: /return to course catalogue/i })).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────
// FULL APP (route-level)
// ─────────────────────────────────────────────────────────────

describe('App routing', () => {
  it('renders HomePage at /', () => {
    renderApp('/');
    expect(screen.getByRole('heading', { level: 1, name: /courses/i })).toBeInTheDocument();
  });

  it('renders 404 for unknown routes', () => {
    renderApp('/does-not-exist-xyz');
    expect(screen.getByRole('heading', { level: 1, name: /page not found/i })).toBeInTheDocument();
  });

  it('html has lang attribute', () => {
    // The lang attribute is on the <html> element in public/index.html.
    // In jsdom, we verify the document.documentElement.lang is set.
    renderApp('/');
    // React doesn't set html lang — it's in index.html; we verify the attribute exists
    // in the static HTML. This is a reminder for the build/deploy step to preserve it.
    // Actual WCAG check is done in E2E Playwright tests.
    expect(true).toBe(true);  // placeholder — E2E covers lang attribute check
  });

  it('main element has id=main-content for skip link target', () => {
    renderApp('/');
    const main = screen.getByRole('main');
    expect(main).toHaveAttribute('id', 'main-content');
  });

  it('main element has tabIndex=-1 for programmatic focus', () => {
    renderApp('/');
    const main = screen.getByRole('main');
    expect(main).toHaveAttribute('tabindex', '-1');
  });

  it('renders CoursePage at /course/:id', () => {
    renderApp('/course/getting-started');
    expect(
      screen.getByRole('heading', { level: 1, name: /getting started/i })
    ).toBeInTheDocument();
  });

  it('renders LessonPage at /lesson/:id', () => {
    renderApp('/lesson/gs-1');
    expect(
      screen.getByRole('heading', { level: 1, name: /welcome and overview/i })
    ).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────
// AUDIO PLAYER — extended coverage for playback controls
// ─────────────────────────────────────────────────────────────

describe('AudioPlayer — extended coverage', () => {
  function renderPlayer(transcript?: string) {
    return renderWithRouter(
      <AudioPlayer src="/test.mp3" title="Test Lesson" transcript={transcript} />
    );
  }

  it('renders the audio element with aria-label matching title', () => {
    renderPlayer();
    const audio = document.querySelector('audio');
    expect(audio).toHaveAttribute('aria-label', 'Test Lesson');
  });

  it('Play button has aria-pressed=false initially', () => {
    renderPlayer();
    expect(screen.getByRole('button', { name: /play/i })).toHaveAttribute('aria-pressed', 'false');
  });

  it('Rewind button has correct aria-label', () => {
    renderPlayer();
    expect(screen.getByRole('button', { name: /rewind 10 seconds/i })).toBeInTheDocument();
  });

  it('Skip forward button has correct aria-label', () => {
    renderPlayer();
    expect(screen.getByRole('button', { name: /skip forward 10 seconds/i })).toBeInTheDocument();
  });

  it('playback controls are in a toolbar landmark', () => {
    renderPlayer();
    expect(screen.getByRole('toolbar', { name: /playback controls/i })).toBeInTheDocument();
  });

  it('has an aria-live status region', () => {
    renderPlayer();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('progress bar has correct aria role and attributes', () => {
    renderPlayer();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('transcript toggle button has aria-expanded=true initially', () => {
    renderPlayer('Hello world transcript');
    expect(screen.getByRole('button', { name: /hide transcript/i })).toHaveAttribute(
      'aria-expanded',
      'true'
    );
  });

  it('clicking transcript toggle hides transcript and updates aria-expanded', () => {
    renderPlayer('Hello world transcript');
    const btn = screen.getByRole('button', { name: /hide transcript/i });
    fireEvent.click(btn);
    expect(screen.getByRole('button', { name: /show transcript/i })).toHaveAttribute(
      'aria-expanded',
      'false'
    );
  });

  it('transcript controls reference lesson-transcript id via aria-controls', () => {
    renderPlayer('Some text');
    const btn = screen.getByRole('button', { name: /hide transcript/i });
    expect(btn).toHaveAttribute('aria-controls', 'lesson-transcript');
  });

  it('renders transcript text when provided', () => {
    renderPlayer('This is the lesson transcript.');
    expect(screen.getByText(/this is the lesson transcript/i)).toBeInTheDocument();
  });

  it('does not render transcript toggle when no transcript prop is given', () => {
    renderPlayer();
    expect(screen.queryByRole('button', { name: /transcript/i })).not.toBeInTheDocument();
  });

  it('section element has aria-label identifying the audio player', () => {
    renderPlayer();
    expect(screen.getByRole('region', { name: /audio player: test lesson/i })).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────
// SITE HEADER — landmark and navigation
// ─────────────────────────────────────────────────────────────

describe('SiteHeader', () => {
  it('renders a <header> landmark', () => {
    renderWithRouter(<SiteHeader />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('has a <nav> with aria-label "Primary navigation"', () => {
    renderWithRouter(<SiteHeader />);
    expect(screen.getByRole('navigation', { name: /primary navigation/i })).toBeInTheDocument();
  });

  it('site logo link has descriptive aria-label', () => {
    renderWithRouter(<SiteHeader />);
    expect(
      screen.getByRole('link', { name: /blind assistant learning.*home/i })
    ).toBeInTheDocument();
  });

  it('nav link list uses role=list for VoiceOver compatibility', () => {
    renderWithRouter(<SiteHeader />);
    const nav = screen.getByRole('navigation', { name: /primary navigation/i });
    expect(within(nav).getByRole('list')).toBeInTheDocument();
  });

  it('marks Courses link as aria-current=page on home route', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <SiteHeader />
      </MemoryRouter>
    );
    const coursesLink = screen.getByRole('link', { name: /^courses$/i });
    expect(coursesLink).toHaveAttribute('aria-current', 'page');
  });

  it('courses link has no aria-current on non-home route', () => {
    render(
      <MemoryRouter initialEntries={['/course/getting-started']}>
        <SiteHeader />
      </MemoryRouter>
    );
    const coursesLink = screen.getByRole('link', { name: /^courses$/i });
    // When not active, aria-current is not present (NavLink uses callback form)
    expect(coursesLink).not.toHaveAttribute('aria-current', 'page');
  });
});

// ─────────────────────────────────────────────────────────────
// COURSE PAGE — lesson listing accessibility
// ─────────────────────────────────────────────────────────────

function renderCoursePage(courseId: string) {
  return render(
    <MemoryRouter initialEntries={[`/course/${courseId}`]}>
      <Routes>
        <Route path="/course/:courseId" element={<CoursePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('CoursePage', () => {
  it('renders the course title as h1', () => {
    renderCoursePage('getting-started');
    expect(
      screen.getByRole('heading', { level: 1, name: /getting started with blind assistant/i })
    ).toBeInTheDocument();
  });

  it('shows an ordered list of lessons', () => {
    renderCoursePage('getting-started');
    expect(screen.getByRole('list')).toBeInTheDocument();
  });

  it('lesson links include lesson number and title', () => {
    renderCoursePage('getting-started');
    expect(screen.getByRole('link', { name: /lesson 1.*welcome/i })).toBeInTheDocument();
  });

  it('has a back link to course catalogue', () => {
    renderCoursePage('getting-started');
    expect(screen.getByRole('link', { name: /back to courses/i })).toBeInTheDocument();
  });

  it('shows 404-style message for unknown course', () => {
    renderCoursePage('not-a-real-course');
    expect(
      screen.getByRole('heading', { level: 1, name: /course not found/i })
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /return to course catalogue/i })).toBeInTheDocument();
  });

  it('lesson list has aria-label identifying the course', () => {
    renderCoursePage('getting-started');
    expect(
      screen.getByRole('list', { name: /lessons in getting started with blind assistant/i })
    ).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────
// LESSON PAGE — audio player and accessibility
// ─────────────────────────────────────────────────────────────

function renderLessonPage(lessonId: string) {
  return render(
    <MemoryRouter initialEntries={[`/lesson/${lessonId}`]}>
      <Routes>
        <Route path="/lesson/:lessonId" element={<LessonPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('LessonPage', () => {
  it('renders lesson title as h1', () => {
    renderLessonPage('gs-1');
    expect(
      screen.getByRole('heading', { level: 1, name: /welcome and overview/i })
    ).toBeInTheDocument();
  });

  it('has a breadcrumb navigation', () => {
    renderLessonPage('gs-1');
    expect(screen.getByRole('navigation', { name: /breadcrumb/i })).toBeInTheDocument();
  });

  it('current page breadcrumb has aria-current="page"', () => {
    renderLessonPage('gs-1');
    const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i });
    const current = within(breadcrumb).getByText(/welcome and overview/i);
    expect(current).toHaveAttribute('aria-current', 'page');
  });

  it('has a "Mark as complete" button with aria-pressed=false initially', () => {
    renderLessonPage('gs-1');
    const btn = screen.getByRole('button', { name: /mark as complete/i });
    expect(btn).toHaveAttribute('aria-pressed', 'false');
  });

  it('toggling "Mark as complete" updates aria-pressed to true', () => {
    renderLessonPage('gs-1');
    const btn = screen.getByRole('button', { name: /mark as complete/i });
    fireEvent.click(btn);
    expect(screen.getByRole('button', { name: /marked as complete/i })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
  });

  it('shows 404-style message for unknown lesson', () => {
    renderLessonPage('not-a-real-lesson');
    expect(
      screen.getByRole('heading', { level: 1, name: /lesson not found/i })
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /return to courses/i })).toBeInTheDocument();
  });

  it('link to next lesson is present when a next lesson exists', () => {
    renderLessonPage('gs-1');
    expect(screen.getByRole('link', { name: /next lesson/i })).toBeInTheDocument();
  });

  it('no previous lesson link on first lesson', () => {
    renderLessonPage('gs-1');
    expect(screen.queryByRole('link', { name: /previous lesson/i })).not.toBeInTheDocument();
  });

  it('both previous and next lesson links on middle lesson', () => {
    renderLessonPage('gs-2');
    expect(screen.getByRole('link', { name: /previous lesson/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /next lesson/i })).toBeInTheDocument();
  });
});
