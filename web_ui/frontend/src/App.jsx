import { BrowserRouter, Routes, Route } from 'react-router-dom';
import WorkListPage from './pages/WorkListPage';
import WorkDetailPage from './pages/WorkDetailPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>Book Review Interface</h1>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<WorkListPage />} />
            <Route path="/work/:workId" element={<WorkDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
