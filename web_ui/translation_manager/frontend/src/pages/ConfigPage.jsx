import React, { useState } from 'react';

function ConfigPage() {
  const [config, setConfig] = useState({
    catalogPath: '/Users/jacki/project_files/translation_project/wuxia_catalog.db',
    sourceDir: '/Users/jacki/project_files/translation_project/wuxia_individual_files',
    outputDir: '/Users/jacki/project_files/translation_project/translations',
    logDir: './logs',
    backendPort: 8001,
  });

  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // In a real implementation, this would save to backend
    console.log('Saving configuration:', config);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div>
      <h2>Configuration</h2>

      <div className="card">
        <h3 className="mb-2">Backend Settings</h3>

        <div className="form-group">
          <label>Catalog Database Path</label>
          <input
            type="text"
            className="input"
            value={config.catalogPath}
            onChange={(e) => setConfig({ ...config, catalogPath: e.target.value })}
          />
          <span className="help-text">
            Path to wuxia_catalog.db SQLite database containing work metadata
          </span>
        </div>

        <div className="form-group">
          <label>Source Directory</label>
          <input
            type="text"
            className="input"
            value={config.sourceDir}
            onChange={(e) => setConfig({ ...config, sourceDir: e.target.value })}
          />
          <span className="help-text">
            Directory containing wuxia_* folders with source JSON files
          </span>
        </div>

        <div className="form-group">
          <label>Output Directory</label>
          <input
            type="text"
            className="input"
            value={config.outputDir}
            onChange={(e) => setConfig({ ...config, outputDir: e.target.value })}
          />
          <span className="help-text">
            Directory where translated files will be saved
          </span>
        </div>

        <div className="form-group">
          <label>Log Directory</label>
          <input
            type="text"
            className="input"
            value={config.logDir}
            onChange={(e) => setConfig({ ...config, logDir: e.target.value })}
          />
          <span className="help-text">
            Directory for translation job logs
          </span>
        </div>

        <div className="form-group">
          <label>Backend Port</label>
          <input
            type="number"
            className="input"
            value={config.backendPort}
            onChange={(e) => setConfig({ ...config, backendPort: parseInt(e.target.value) })}
          />
          <span className="help-text">
            Port for backend API server (default: 8001)
          </span>
        </div>

        <button
          className="btn btn-success"
          onClick={handleSave}
        >
          {saved ? '✓ Saved!' : 'Save Configuration'}
        </button>
      </div>

      <div className="card mt-2">
        <h3 className="mb-2">System Information</h3>

        <div className="form-group">
          <label>Backend API URL</label>
          <div className="text-muted">
            {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}
          </div>
        </div>

        <div className="form-group">
          <label>Translation Pipeline</label>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '4px', fontSize: '14px' }}>
            <ol style={{ marginLeft: '20px' }}>
              <li>Topology Analysis - Analyze JSON structure</li>
              <li>Sanity Check - Validate metadata and chapters</li>
              <li>JSON Cleaning - Extract and structure content</li>
              <li>Chapter Alignment - Fix TOC/chapter mismatches</li>
              <li>TOC Restructuring - Convert TOC to structured format</li>
              <li>Validation - Comprehensive structure validation</li>
              <li>Translation - AI-powered content translation</li>
            </ol>
          </div>
        </div>

        <div className="form-group">
          <label>Environment Variables</label>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '4px', fontSize: '14px' }}>
            <div className="mb-1">
              <strong>CATALOG_DB_PATH</strong>: Path to catalog database
            </div>
            <div className="mb-1">
              <strong>SOURCE_DIR</strong>: Source files directory
            </div>
            <div className="mb-1">
              <strong>OUTPUT_DIR</strong>: Output directory
            </div>
            <div className="mb-1">
              <strong>OPENAI_API_KEY</strong>: OpenAI API key (loaded from env_creds.yml)
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-2">
        <h3 className="mb-2">Quick Start Guide</h3>

        <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
          <h4>1. Backend Setup</h4>
          <pre style={{ background: '#2c3e50', color: '#ecf0f1', padding: '15px', borderRadius: '4px', overflow: 'auto' }}>
            cd web_ui/translation_manager/backend
            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt
            cp .env.example .env
            # Edit .env with your paths
            python app.py
          </pre>

          <h4 className="mt-2">2. Frontend Setup</h4>
          <pre style={{ background: '#2c3e50', color: '#ecf0f1', padding: '15px', borderRadius: '4px', overflow: 'auto' }}>
            cd web_ui/translation_manager/frontend
            npm install
            npm run dev
          </pre>

          <h4 className="mt-2">3. Access Application</h4>
          <div className="mb-1">• Backend API: <a href="http://localhost:8001" target="_blank">http://localhost:8001</a></div>
          <div className="mb-1">• Frontend UI: <a href="http://localhost:5174" target="_blank">http://localhost:5174</a></div>
          <div className="mb-1">• API Docs: <a href="http://localhost:8001/docs" target="_blank">http://localhost:8001/docs</a></div>
        </div>
      </div>
    </div>
  );
}

export default ConfigPage;
