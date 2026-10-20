import React, { useState, useEffect } from 'react';
import { Header, NavItem } from './components/Header';
import { PowerChatPage } from './pages/PowerChatPage';
import { ChatPage } from './pages/ChatPage';
import { MemoryPage } from './pages/MemoryPage';
import { ToolsPage } from './pages/ToolsPage';
import { VisionPage } from './pages/VisionPage';
import { ImageLabPage } from './pages/ImageLabPage';
import { CodingAgentPage } from './pages/CodingAgentPage';
import { AutomationPage } from './pages/AutomationPage';
import { DiagnosticsPage } from './pages/DiagnosticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { ModelManagerModal } from './components/ModelManagerModal';
import { api } from './services/api';
import { ModelDetails } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavItem>('power');
  const [models, setModels] = useState<ModelDetails[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gemma4:12b');
  const [ollamaOnline, setOllamaOnline] = useState<boolean>(false);
  const [comfyOnline, setComfyOnline] = useState<boolean>(false);
  const [workspacePath, setWorkspacePath] = useState<string>('');
  const [isModelManagerOpen, setIsModelManagerOpen] = useState<boolean>(false);

  // Enforce light mode strictly across HTML body
  useEffect(() => {
    document.body.classList.add('light');
    document.documentElement.classList.add('light');
  }, []);

  // Model refresh callback
  const refreshModels = async () => {
    try {
      const modelList = await api.listModels();
      setModels(modelList);
    } catch (e) {
      console.error('Error refreshing models:', e);
    }
  };

  // Initial startup sync with backend
  useEffect(() => {
    const initApp = async () => {
      try {
        const diag = await api.getDiagnostics();
        setOllamaOnline(diag.ollama.status === 'healthy');
        setComfyOnline(diag.comfyui.status === 'healthy');
        setWorkspacePath(diag.workspace.endpoint || '');

        const modelList = await api.listModels();
        setModels(modelList);
        if (modelList.length > 0) {
          const preferred = modelList.find(m => m.is_preferred);
          setSelectedModel(preferred ? preferred.name : modelList[0].name);
        }
      } catch (e) {
        console.error('Initial connectivity sync error:', e);
      }
    };

    initApp();
    const interval = setInterval(initApp, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-canvas text-main font-sans">
      {/* Top Workstation Navigation Bar (replaces sidebar) */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        models={models}
        ollamaOnline={ollamaOnline}
        comfyOnline={comfyOnline}
        workspacePath={workspacePath}
        onOpenModelManager={() => setIsModelManagerOpen(true)}
      />

      {/* Main Workspace Surface */}
      <main className="flex-1 overflow-hidden relative flex flex-col min-w-0 bg-canvas">
        {activeTab === 'power' && (
          <PowerChatPage
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            models={models}
            onRefreshModels={refreshModels}
          />
        )}
        {activeTab === 'chat' && (
          <ChatPage
            selectedModel={selectedModel}
            models={models}
            ollamaOnline={ollamaOnline}
          />
        )}
        {activeTab === 'memory' && <MemoryPage />}
        {activeTab === 'tools' && <ToolsPage />}
        {activeTab === 'vision' && (
          <VisionPage
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            models={models}
          />
        )}
        {activeTab === 'image_lab' && <ImageLabPage />}
        {activeTab === 'coding' && <CodingAgentPage />}
        {activeTab === 'automation' && <AutomationPage />}
        {activeTab === 'diagnostics' && <DiagnosticsPage />}
        {activeTab === 'settings' && (
          <SettingsPage
            theme="light"
            setTheme={() => {}}
            models={models}
          />
        )}
      </main>

      {/* Global Model Manager Modal */}
      <ModelManagerModal
        isOpen={isModelManagerOpen}
        onClose={() => setIsModelManagerOpen(false)}
        models={models}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        onRefreshModels={refreshModels}
      />
    </div>
  );
};
