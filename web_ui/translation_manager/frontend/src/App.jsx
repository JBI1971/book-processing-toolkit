import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import WorkListPage from './pages/WorkListPage';
import JobsPage from './pages/JobsPage';
import ConfigPage from './pages/ConfigPage';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="header">
          <div className="container">
            <h1>Translation Manager</h1>
            <p>Book Processing Toolkit - Translation Management Interface</p>
            <nav style={{ marginTop: '15px' }}>
              <Link to="/" style={linkStyle}>📚 Works Catalog</Link>
              {' | '}
              <Link to="/jobs" style={linkStyle}>⚙️ Translation Jobs</Link>
              {' | '}
              <Link to="/config" style={linkStyle}>🔧 Configuration</Link>
            </nav>
          </div>
        </header>

        <div className="container">
          <Routes>
            <Route path="/" element={<WorkListPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/config" element={<ConfigPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

const linkStyle = {
  color: '#3498db',
  textDecoration: 'none',
  fontWeight: 500,
  padding: '5px 10px',
};

export default App;
