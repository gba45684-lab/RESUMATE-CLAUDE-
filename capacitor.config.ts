import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.krapal.resumeforge',
  appName: 'ResuMate',
  webDir: 'www',
  plugins: {
    CapacitorUpdater: {
      appId: 'com.krapal.resumeforge',
      updateUrl: 'https://resumate-claude.vercel.app/api/updates',
      autoUpdate: 'atBackground',
      version: '1.0.0',
      appReadyTimeout: 10000,
      autoDeleteFailed: true,
      autoDeletePrevious: true
    }
  }
};

export default config;
