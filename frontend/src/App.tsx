import { Navigate, Route, Routes } from 'react-router-dom';
import ReposPage from './pages/ReposPage';
import RepoView from './pages/RepoView';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ReposPage />} />
      <Route path="/repos/:repoId/*" element={<RepoView />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
