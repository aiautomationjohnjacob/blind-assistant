/**
 * Root application component for Blind Assistant Learning Platform.
 *
 * Routing:
 *   /          → Home (course catalogue)
 *   /course/:id → Course detail + lesson list
 *   /lesson/:id → Individual lesson player (audio-primary)
 *
 * Accessibility contract:
 * - After every route change, focus moves to the main <h1> so NVDA / VoiceOver
 *   announces the new page without requiring the user to navigate.
 * - A skip link in index.html is always the first focusable element.
 * - aria-live="polite" status region sits at the top of every page for
 *   real-time announcements (lesson progress, loading state, errors).
 */

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import SiteHeader from './components/SiteHeader';
import SiteFooter from './components/SiteFooter';
import HomePage from './pages/HomePage';
import CoursePage from './pages/CoursePage';
import LessonPage from './pages/LessonPage';
import NotFoundPage from './pages/NotFoundPage';

function App(): React.ReactElement {
  return (
    <>
      <SiteHeader />
      <main id="main-content" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/course/:courseId" element={<CoursePage />} />
          <Route path="/lesson/:lessonId" element={<LessonPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
      <SiteFooter />
    </>
  );
}

export default App;
