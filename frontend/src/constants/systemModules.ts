export interface SystemModule {
  id: string;
  label: string;
  icon?: string;
  path?: string;
  children?: SystemModule[];
}

export const SYSTEM_MODULES: SystemModule[] = [];
