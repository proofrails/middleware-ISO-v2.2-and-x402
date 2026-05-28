import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext';
import { AppLayout } from './components/layout/AppLayout';
import { CreateRecordPage } from './pages/CreateRecordPage';
import { RecordDetailPage } from './pages/RecordDetailPage';
import { RecordsPage } from './pages/RecordsPage';
import { SettingsPage } from './pages/SettingsPage';
import { VerifyPage } from './pages/VerifyPage';
import { DocsPage } from './pages/DocsPage';

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/records" replace />} />
            <Route path="/records" element={<RecordsPage />} />
            <Route path="/records/create" element={<CreateRecordPage />} />
            <Route path="/records/:recordId" element={<RecordDetailPage />} />
            <Route path="/verify" element={<VerifyPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/docs" element={<DocsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}
