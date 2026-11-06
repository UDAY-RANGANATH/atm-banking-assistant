import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import LanguageSelect from './pages/LanguageSelect'
import { DocumentChecklistPage } from './pages/DocumentChecklistPage'
import { DocumentScannerPage } from './pages/DocumentScannerPage'
import { ApplicationFormPage } from './pages/ApplicationFormPage'
import { PdfExportPage } from './pages/PdfExportPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LanguageSelect />} />
        <Route path="/home" element={<Home />} />
        <Route path="/documents/:serviceId" element={<DocumentChecklistPage />} />
        <Route path="/scan/:serviceId/:documentId" element={<DocumentScannerPage />} />
        <Route path="/application/form/:serviceId" element={<ApplicationFormPage />} />
        <Route path="/application/pdf/:serviceId" element={<PdfExportPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
