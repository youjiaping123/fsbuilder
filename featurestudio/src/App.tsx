import { useState } from 'react';
import { 
  Bell, 
  UserCircle, 
  CheckCircle2, 
  Box, 
  Link, 
  AlertTriangle, 
  Wand2, 
  Upload, 
  Info, 
  Ruler, 
  Move, 
  Layers, 
  Copy, 
  Download, 
  ExternalLink, 
  BarChart3, 
  ClipboardCheck, 
  Code2, 
  Hammer, 
  Play,
  CheckCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Part, AssemblyRelation, AppState } from './types';

const INITIAL_PARTS: Part[] = [
  {
    id: 'P001',
    name: '下模座',
    englishName: 'Lower Die Seat',
    shape: 'Box',
    material: 'Steel 4130',
    status: 'stable',
    geometry: { width: 450, depth: 300, height: 80 },
    position: { x: 0, y: 0, z: 0 },
    description: '基础模座，通过4个螺栓固定在工作台上。预留四个导柱安装孔位。'
  },
  {
    id: 'P002',
    name: '拉伸模',
    englishName: 'Drawing Die',
    shape: 'Hollow Cyl',
    material: 'Steel 4130',
    status: 'error',
    geometry: { radius: 150, innerRadius: 100, height: 120 },
    position: { x: 0, y: 0, z: 80 },
    description: '核心拉伸成型部件，内腔形状需精确匹配覆盖件。'
  },
  {
    id: 'P003',
    name: '压料板',
    englishName: 'Blank Holder',
    shape: 'Hollow Cyl',
    material: 'Steel 4130',
    status: 'stable',
    geometry: { radius: 180, innerRadius: 155, height: 40 },
    position: { x: 0, y: 0, z: 200 },
    description: '压紧板料，防止拉伸过程中产生起皱。'
  },
  {
    id: 'P004',
    name: '上模座',
    englishName: 'Upper Die Seat',
    shape: 'Box',
    material: 'Steel 4130',
    status: 'stable',
    geometry: { width: 450, depth: 300, height: 60 },
    position: { x: 0, y: 0, z: 300 },
    description: '安装在压力机滑块上，带动上模部分运动。'
  }
];

const INITIAL_RELATIONS: AssemblyRelation[] = [
  { sourcePartId: 'P002', relation: 'stacked_on', targetPartId: 'P001' },
  { sourcePartId: 'P003', relation: 'stacked_on', targetPartId: 'P002' },
  { sourcePartId: 'P004', relation: 'guided_by', targetPartId: 'P001' },
  { sourcePartId: 'P005', relation: 'stacked_on', targetPartId: 'P004' }
];

export default function App() {
  const [state, setState] = useState<AppState>({
    requirements: '',
    runMode: 'analyze',
    parts: INITIAL_PARTS,
    relations: INITIAL_RELATIONS,
    selectedPartId: 'P001',
    activeTab: 'parts',
    outputTab: 'fs'
  });

  const selectedPart = state.parts.find(p => p.id === state.selectedPartId);

  const handlePartSelect = (id: string) => {
    setState(prev => ({ ...prev, selectedPartId: id }));
  };

  return (
    <div className="flex flex-col h-screen bg-surface text-on-surface overflow-hidden">
      {/* Header */}
      <header className="h-12 flex justify-between items-center px-6 border-b border-outline-variant/10 bg-surface-container-lowest z-50">
        <div className="flex items-center gap-8">
          <span className="text-lg font-black tracking-tighter text-on-surface">FeatureStudio</span>
          <nav className="flex gap-6 items-center h-12">
            <button className="text-sm font-semibold text-primary border-b-2 border-primary h-full px-1">Workspace</button>
            <button className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors">Examples</button>
            <button className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors">Settings</button>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative cursor-pointer p-1.5 rounded-full hover:bg-surface-container-high transition-colors">
            <Bell className="w-5 h-5 text-on-surface-variant" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full border border-surface"></span>
          </div>
          <UserCircle className="w-6 h-6 text-on-surface-variant cursor-pointer hover:text-primary transition-colors" />
        </div>
      </header>

      {/* Status Bar */}
      <div className="h-8 bg-surface-container-low flex items-center px-6 gap-4 text-[11px] font-medium border-b border-outline-variant/10 text-on-surface-variant">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-tertiary" />
          <span>需求已加载</span>
        </div>
        <span className="opacity-30">|</span>
        <div className="flex items-center gap-1.5">
          <Box className="w-3.5 h-3.5" />
          <span>{state.parts.length} 个零件</span>
        </div>
        <span className="opacity-30">|</span>
        <div className="flex items-center gap-1.5">
          <Link className="w-3.5 h-3.5" />
          <span>{state.relations.length} 个装配关系</span>
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-error font-bold">
          <AlertTriangle className="w-3.5 h-3.5 fill-error/20" />
          <span>校验失败：1 个问题</span>
        </div>
      </div>

      <main className="flex-1 grid grid-cols-12 overflow-hidden">
        {/* Left Column: Task Setup */}
        <section className="col-span-3 bg-surface-container-low flex flex-col p-4 gap-6 overflow-y-auto no-scrollbar border-r border-outline-variant/10">
          <div className="space-y-1">
            <h2 className="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">需求输入 Requirement Input</h2>
            <div className="h-0.5 w-6 bg-primary rounded-full"></div>
          </div>

          <div className="space-y-3">
            <div className="relative group">
              <textarea 
                className="w-full h-48 bg-surface-container-lowest p-3 text-sm rounded-xl border-none focus:ring-1 focus:ring-primary/20 placeholder:text-outline-variant/40 resize-none shadow-sm transition-all"
                placeholder="描述您的装配需求，例如：设计一个用于汽车覆盖件拉伸的冷冲压模具..."
                value={state.requirements}
                onChange={(e) => setState(prev => ({ ...prev, requirements: e.target.value }))}
              />
              <button className="absolute bottom-3 right-3 p-2 rounded-lg bg-surface-container-high text-primary hover:bg-primary-container transition-all opacity-0 group-hover:opacity-100 shadow-sm">
                <Wand2 className="w-4 h-4" />
              </button>
            </div>
            <button className="w-full py-2.5 bg-surface-container-high text-on-surface text-xs font-semibold rounded-xl hover:bg-surface-container-highest flex items-center justify-center gap-2 border border-outline-variant/5 transition-colors">
              <Upload className="w-4 h-4" />
              上传 .txt
            </button>
          </div>

          <div className="space-y-3">
            <label className="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">运行模式 Run Mode</label>
            <div className="space-y-1">
              {[
                { id: 'analyze', label: 'Analyze Only', desc: '仅进行逻辑与几何冲突分析' },
                { id: 'generate', label: 'Generate from Plan', desc: '基于既有方案生成 FeatureScript' },
                { id: 'full', label: 'Full Build', desc: '从需求到完整 FS 链条的自动构建' }
              ].map((mode) => (
                <label key={mode.id} className={`flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all ${state.runMode === mode.id ? 'bg-primary-container/40 ring-1 ring-primary/20' : 'hover:bg-surface-container-high'}`}>
                  <input 
                    type="radio" 
                    name="runMode" 
                    className="mt-1 text-primary focus:ring-0 bg-transparent border-outline-variant"
                    checked={state.runMode === mode.id}
                    onChange={() => setState(prev => ({ ...prev, runMode: mode.id as any }))}
                  />
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-on-surface">{mode.label}</span>
                    <span className="text-[10px] text-on-surface-variant leading-relaxed">{mode.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <label className="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">示例模板 Quick Start</label>
            <div className="flex flex-wrap gap-2">
              {['冷拉延模具', '简单夹具', '法兰组件'].map(tag => (
                <button key={tag} className="px-3 py-1.5 bg-surface-container-highest text-on-surface text-[10px] font-bold rounded-lg hover:bg-primary-container hover:text-on-primary-container transition-all">
                  {tag}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-auto pt-4 border-t border-outline-variant/5">
            <p className="text-[9px] text-on-surface-variant/60 font-medium leading-relaxed">
              Capability Boundary 当前支持：<br/>
              box, cylinder, hollow cylinder, tapered cylinder, flange
            </p>
          </div>
        </section>

        {/* Middle Column: Assembly Plan Editor */}
        <section className="col-span-5 flex flex-col overflow-hidden bg-surface">
          {/* Tabs */}
          <div className="flex items-center px-4 h-10 border-b border-outline-variant/10">
            <div className="flex gap-6 h-full items-center">
              {['JSON 方案', '零件列表', '校验'].map((tab, i) => {
                const id = ['json', 'parts', 'validation'][i] as any;
                const active = state.activeTab === id;
                return (
                  <button 
                    key={id}
                    onClick={() => setState(prev => ({ ...prev, activeTab: id }))}
                    className={`text-xs font-bold px-1 h-full relative transition-colors ${active ? 'text-primary' : 'text-on-surface-variant hover:text-on-surface'}`}
                  >
                    {tab}
                    {active && <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 w-full h-0.5 bg-primary" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Part Navigator */}
          <div className="bg-surface-container-low/50 px-4 py-4 flex gap-3 overflow-x-auto no-scrollbar border-b border-outline-variant/5">
            {state.parts.map(part => {
              const active = state.selectedPartId === part.id;
              return (
                <motion.div 
                  key={part.id}
                  whileHover={{ y: -2 }}
                  onClick={() => handlePartSelect(part.id)}
                  className={`min-w-[150px] p-3 rounded-xl shadow-sm cursor-pointer transition-all border-l-4 ${
                    active 
                      ? 'bg-primary-container border-primary' 
                      : part.status === 'error' 
                        ? 'bg-surface-container-lowest border-error' 
                        : 'bg-surface-container-lowest border-tertiary'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex flex-col">
                      <span className={`text-[11px] font-bold leading-tight ${active ? 'text-on-primary-container' : 'text-on-surface'}`}>{part.name}</span>
                      <span className={`text-[9px] font-medium opacity-60 ${active ? 'text-on-primary-container' : 'text-on-surface-variant'}`}>{part.englishName}</span>
                    </div>
                    <span className={`text-[9px] font-mono font-bold opacity-40 ${active ? 'text-on-primary-container' : 'text-on-surface-variant'}`}>{part.id}</span>
                  </div>
                  <div className="flex justify-between items-end mt-3">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${active ? 'bg-white/30 text-on-primary-container' : 'bg-surface-container-high text-on-surface-variant'}`}>
                      {part.shape}
                    </span>
                    {part.status === 'stable' ? (
                      <CheckCircle className={`w-3.5 h-3.5 ${active ? 'text-primary' : 'text-tertiary'}`} />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-error fill-error/10" />
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Part Editor */}
          <div className="flex-1 overflow-y-auto p-8 flex flex-col gap-8 no-scrollbar">
            <AnimatePresence mode="wait">
              {selectedPart && (
                <motion.div 
                  key={selectedPart.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-8"
                >
                  {/* Basic Info */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                        <Info className="w-5 h-5" />
                      </div>
                      <h3 className="text-sm font-bold text-on-surface">基础信息</h3>
                    </div>
                    <div className="grid grid-cols-3 gap-6 bg-surface-container-low p-5 rounded-2xl">
                      {[
                        { label: 'Part ID', value: selectedPart.id, mono: true },
                        { label: 'Shape', value: selectedPart.shape },
                        { label: 'Material', value: selectedPart.material }
                      ].map(item => (
                        <div key={item.label} className="flex flex-col gap-1">
                          <span className="text-[9px] uppercase text-on-surface-variant font-bold tracking-wider">{item.label}</span>
                          <span className={`text-xs font-bold text-on-surface ${item.mono ? 'font-mono' : ''}`}>{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Geometry */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                        <Ruler className="w-5 h-5" />
                      </div>
                      <h3 className="text-sm font-bold text-on-surface">几何参数 Geometry</h3>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      {Object.entries(selectedPart.geometry).map(([key, val]) => (
                        <div key={key} className="flex flex-col gap-2">
                          <label className="text-[10px] text-on-surface-variant font-bold uppercase tracking-wider">{key} (mm)</label>
                          <input 
                            type="text" 
                            className="bg-surface-container-low border-none border-b-2 border-transparent focus:border-primary focus:ring-0 rounded-xl p-3 text-xs font-mono font-bold transition-all"
                            value={(val as number).toFixed(2)}
                            readOnly
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Position */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                        <Move className="w-5 h-5" />
                      </div>
                      <h3 className="text-sm font-bold text-on-surface">位置参数 Position</h3>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      {Object.entries(selectedPart.position).map(([key, val]) => (
                        <div key={key} className="flex flex-col gap-2">
                          <label className="text-[10px] text-on-surface-variant font-bold uppercase tracking-wider">{key.toUpperCase()} (mm)</label>
                          <input 
                            type="text" 
                            className="bg-surface-container-low border-none border-b-2 border-transparent focus:border-primary focus:ring-0 rounded-xl p-3 text-xs font-mono font-bold transition-all"
                            value={(val as number).toFixed(2)}
                            readOnly
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Description */}
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-on-surface-variant tracking-widest uppercase">零件描述 Description</label>
                    <div className="p-4 bg-surface-container-low rounded-2xl text-xs leading-relaxed text-on-surface-variant font-medium">
                      {selectedPart.description}
                    </div>
                  </div>

                  {/* Assembly Relations */}
                  <div className="space-y-4 pt-4 border-t border-outline-variant/10">
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                        <Layers className="w-5 h-5" />
                      </div>
                      <h3 className="text-sm font-bold text-on-surface">装配关系 Assembly Relations</h3>
                    </div>
                    <div className="space-y-1">
                      {state.relations.filter(r => r.sourcePartId === selectedPart.id || r.targetPartId === selectedPart.id).map((rel, i) => (
                        <div key={i} className="flex items-center gap-4 p-3 rounded-xl hover:bg-surface-container-low transition-colors group">
                          <div className="w-2 h-2 rounded-full bg-primary/40 group-hover:bg-primary transition-colors"></div>
                          <div className="flex items-center gap-2 text-[11px]">
                            <span className="font-bold text-on-surface">{state.parts.find(p => p.id === rel.sourcePartId)?.name || rel.sourcePartId}</span>
                            <span className="italic text-[10px] text-on-surface-variant opacity-60">{rel.relation}</span>
                            <span className="font-bold text-on-surface">{state.parts.find(p => p.id === rel.targetPartId)?.name || rel.targetPartId}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </section>

        {/* Right Column: Output */}
        <section className="col-span-4 border-l border-outline-variant/15 flex flex-col overflow-hidden bg-inverse-surface">
          {/* Tabs */}
          <div className="flex items-center justify-between px-4 h-10 border-b border-white/5">
            <div className="flex gap-6 h-full items-center">
              {['FeatureScript', '零件摘要', '运行日志'].map((tab, i) => {
                const id = ['fs', 'summary', 'logs'][i] as any;
                const active = state.outputTab === id;
                return (
                  <button 
                    key={id}
                    onClick={() => setState(prev => ({ ...prev, outputTab: id }))}
                    className={`text-[10px] font-bold px-1 h-full relative transition-colors ${active ? 'text-blue-400' : 'text-white/40 hover:text-white/70'}`}
                  >
                    {tab}
                    {active && <motion.div layoutId="activeOutputTab" className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-400" />}
                  </button>
                );
              })}
            </div>
            <div className="flex gap-1">
              <button className="p-1.5 text-white/40 hover:text-blue-400 transition-colors rounded-lg hover:bg-white/5">
                <Copy className="w-4 h-4" />
              </button>
              <button className="p-1.5 text-white/40 hover:text-blue-400 transition-colors rounded-lg hover:bg-white/5">
                <Download className="w-4 h-4" />
              </button>
              <button className="flex items-center gap-1.5 py-1 px-2.5 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-all border border-blue-500/20 ml-1">
                <ExternalLink className="w-3.5 h-3.5" />
                <span className="text-[9px] font-bold uppercase tracking-wider">Onshape</span>
              </button>
            </div>
          </div>

          {/* Code Editor */}
          <div className="flex-1 p-6 font-mono text-[11px] overflow-auto leading-relaxed bg-[#0b0f10] selection:bg-blue-500/30">
            <div className="space-y-1">
              <div className="text-white/20 italic mb-4">// Generated by FeatureStudio v2.1.0</div>
              {[
                { line: 1, content: <><span className="text-blue-400">FeatureScript </span><span className="text-white/90">2399;</span></> },
                { line: 2, content: <><span className="text-purple-400">import</span><span className="text-white/90">(path : </span><span className="text-yellow-200">"onshape/std/geometry.fs"</span><span className="text-white/90">, version : </span><span className="text-yellow-200">"2399.0"</span><span className="text-white/90">);</span></> },
                { line: 3, content: <span>&nbsp;</span> },
                { line: 4, content: <><span className="text-blue-400">annotation </span><span className="text-white/90">{`{ `}</span><span className="text-green-400">"Feature Name" </span><span className="text-white/90">: </span><span className="text-green-400">"Drawing Die" </span><span className="text-white/90">{` }`}</span></> },
                { line: 5, content: <><span className="text-purple-400">export const </span><span className="text-blue-400">drawingDie </span><span className="text-white/90">= </span><span className="text-purple-400">defineFeature</span><span className="text-white/90">(</span><span className="text-purple-400">function</span><span className="text-white/90">(context </span><span className="text-purple-400">is </span><span className="text-white/90">Context, id </span><span className="text-purple-400">is </span><span className="text-white/90">Id, definition </span><span className="text-purple-400">is </span><span className="text-white/90">map)</span></> },
                { line: 6, content: <span className="text-white/90">{`{`}</span> },
                { line: 7, content: <><span className="text-white/90">&nbsp;&nbsp;&nbsp;&nbsp;</span><span className="text-purple-400">fCuboid</span><span className="text-white/90">(context, id + </span><span className="text-green-400">"base"</span><span className="text-white/90">, {`{`}</span></> },
                { line: 8, content: <><span className="text-white/90">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span><span className="text-green-400">"corner1" </span><span className="text-white/90">: </span><span className="text-blue-400">vector</span><span className="text-white/90">(</span><span className="text-orange-300">0</span><span className="text-white/90">, </span><span className="text-orange-300">0</span><span className="text-white/90">, </span><span className="text-orange-300">0</span><span className="text-white/90">) * millimeter,</span></> },
                { line: 9, content: <><span className="text-white/90">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span><span className="text-green-400">"corner2" </span><span className="text-white/90">: </span><span className="text-blue-400">vector</span><span className="text-white/90">(</span><span className="text-orange-300">450</span><span className="text-white/90">, </span><span className="text-orange-300">300</span><span className="text-white/90">, </span><span className="text-orange-300">80</span><span className="text-white/90">) * millimeter</span></> },
                { line: 10, content: <span className="text-white/90">&nbsp;&nbsp;&nbsp;&nbsp;{`});`}</span> },
                { line: 11, content: <span className="text-white/90">{`});`}</span> }
              ].map(row => (
                <div key={row.line} className="flex gap-6 group hover:bg-white/5 transition-colors px-2 -mx-2">
                  <span className="w-6 text-right text-white/10 select-none group-hover:text-white/30">{row.line}</span>
                  <div className="flex-1">{row.content}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Assembly Status */}
          <div className="h-28 bg-[#1a1f21] border-t border-white/5 p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-[9px] text-white/30 uppercase font-bold tracking-[0.2em]">Assembly Stats</span>
              <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-[8px] rounded-full font-bold border border-blue-500/20">STABLE</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Est. Volume', value: '10.8e6 mm³' },
                { label: 'Material WT.', value: '84.24 kg' },
                { label: 'BOM Count', value: '005 Items' }
              ].map(stat => (
                <div key={stat.label} className="bg-white/5 rounded-xl p-2.5 border border-white/5 flex flex-col gap-1">
                  <span className="text-[8px] text-white/20 uppercase font-bold tracking-wider">{stat.label}</span>
                  <span className="text-[11px] text-white/90 font-mono font-bold">{stat.value}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="h-16 bg-surface-container-low border-t border-outline-variant/10 flex justify-center items-center px-10 gap-10 z-50">
        {[
          { icon: BarChart3, label: 'Analyze' },
          { icon: ClipboardCheck, label: 'Validate' },
          { icon: Code2, label: 'Generate FS', primary: true },
          { icon: Hammer, label: 'Build' },
          { icon: Download, label: 'Download' }
        ].map((item, i) => (
          <button 
            key={i}
            className={`flex flex-col items-center justify-center gap-1.5 transition-all active:scale-95 ${
              item.primary 
                ? 'bg-primary text-white px-10 py-2 rounded-2xl shadow-lg shadow-primary/20 hover:bg-primary-dim' 
                : 'text-on-surface-variant/60 hover:text-primary'
            }`}
          >
            <item.icon className={item.primary ? 'w-5 h-5' : 'w-5 h-5'} />
            <span className="text-[9px] font-bold uppercase tracking-widest">{item.label}</span>
          </button>
        ))}
      </footer>

      {/* FAB */}
      <motion.button 
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="fixed bottom-24 right-8 w-14 h-14 bg-primary text-white rounded-full shadow-2xl flex items-center justify-center hover:bg-primary-dim transition-all z-50"
      >
        <Play className="w-6 h-6 fill-current" />
      </motion.button>
    </div>
  );
}
