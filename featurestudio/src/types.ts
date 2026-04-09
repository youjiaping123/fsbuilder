export type Shape = 'Box' | 'Hollow Cyl' | 'Cylinder' | 'Tapered Cyl' | 'Flange';

export interface Part {
  id: string;
  name: string;
  englishName: string;
  shape: Shape;
  material: string;
  status: 'stable' | 'error' | 'warning';
  geometry: {
    width?: number;
    depth?: number;
    height?: number;
    radius?: number;
    innerRadius?: number;
  };
  position: {
    x: number;
    y: number;
    z: number;
  };
  description: string;
}

export interface AssemblyRelation {
  sourcePartId: string;
  relation: 'stacked_on' | 'guided_by' | 'fixed_to';
  targetPartId: string;
}

export interface AppState {
  requirements: string;
  runMode: 'analyze' | 'generate' | 'full';
  parts: Part[];
  relations: AssemblyRelation[];
  selectedPartId: string | null;
  activeTab: 'json' | 'parts' | 'validation';
  outputTab: 'fs' | 'summary' | 'logs';
}
