/**
 * Entry point for the Blind Assistant Learning Platform.
 *
 * Audio-primary design: after any route change, focus moves to the <h1>
 * so screen readers announce the new page immediately without requiring
 * user navigation. All interactive elements have accessible names.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles/global.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element #root not found in index.html');
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
