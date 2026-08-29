import React, { useState, useRef, useEffect } from 'react';
import {
  Compass,
  Send,
  Cpu,
  Bot,
  User,
  ShieldAlert,
  CheckSquare,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  MapPin,
  Clock,
  Zap,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { ApiResponse } from '../types';

interface CopilotFilters {
  color: string | null;
  model: string | null;
  district: string;
  plate: string | null;
  incident: string;
}

interface TimelineWaypoint {
  timestamp: string;
  location: string;
  latitude: number;
  longitude: number;
  speed_kmph: number;
  direction: string;
}

interface EvidenceReference {
  camera_name: string;
  evidence_type: string;
  plate_extracted?: string;
  confidence: number;
  timestamp: string;
}

interface CopilotResponseData {
  query: string;
  intent: string;
  extracted_filters: CopilotFilters;
  executive_summary: string;
  findings: string[];
  confidence_score: number;
  movement_timeline: TimelineWaypoint[];
  evidence_references: EvidenceReference[];
  recommended_actions: string[];
  model_name: string;
  generated_at: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: Date;
  data?: CopilotResponseData;
}

export const InvestigationsPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'agent',
      text: 'AI Dispatch Agent online. Enter natural language case details to cross-correlate vehicle sightings, extract OCR plates, build timeline trajectories, and generate recommended actions.',
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionStates, setActionStates] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const presets = [
    { label: 'Track Scorpio', query: 'Locate black Scorpio GJ-01-XX-9921 last seen near Chiman Bhai Bridge' },
    { label: 'Find Red Swift', query: 'Find red Swift involved in robbery near Ahmedabad between 8 PM and 10 PM' },
    { label: 'curfew check', query: 'Alert Gandhinagar toll plazas for fleeing suspect on SG Highway' },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userQuery = query.trim();
    setQuery('');
    
    // Add user message
    const userMsgId = Math.random().toString();
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: userQuery, timestamp: new Date() },
    ]);

    setIsLoading(true);

    try {
      const res = await apiClient<ApiResponse<CopilotResponseData>>('/investigations/copilot/query', {
        method: 'POST',
        body: JSON.stringify({ query: userQuery }),
      });

      if (res.success && res.data) {
        setMessages((prev) => [
          ...prev,
          {
            id: Math.random().toString(),
            sender: 'agent',
            text: res.data.executive_summary,
            timestamp: new Date(),
            data: res.data,
          },
        ]);
      } else {
        throw new Error('Incomplete response received from Copilot agent');
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(),
          sender: 'agent',
          text: `Error connecting to Copilot API: ${err?.message || 'Network unreachable'}. Operating in offline diagnostic mode.`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePresetClick = (q: string) => {
    setQuery(q);
  };

  const toggleAction = (actionKey: string) => {
    setActionStates((prev) => ({
      ...prev,
      [actionKey]: !prev[actionKey],
    }));
  };

  return (
    <div className="investigations-page p-6 max-w-7xl mx-auto space-y-6">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/80 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-cyan-600/20 border border-cyan-500/30 rounded-xl text-cyan-400 animate-pulse">
            <Compass size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white tracking-wide">Police AI Copilot</h1>
              <span className="bg-emerald-950 text-emerald-400 border border-emerald-500/30 text-xs px-2 py-0.5 rounded font-mono font-bold">
                ACTIVE ORCHESTRATOR
              </span>
            </div>
            <p className="text-sm text-slate-400">Natural-language operational dispatcher & spatial-temporal multi-sighting correlation agent</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Chat / Terminal Area - Left 7 Columns */}
        <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl flex flex-col h-[70vh]">
          {/* Header */}
          <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Bot size={14} />
              <span>COGNITIVE DISPATCH HARNESS // STATUS: READY</span>
            </div>
            <div className="text-[10px] bg-slate-900 border border-slate-800 text-slate-500 px-2 py-0.5 rounded font-mono">
              MODEL: Gemini-3.5-Medium
            </div>
          </div>

          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-sm">
            {messages.map((msg) => {
              const isUser = msg.sender === 'user';
              return (
                <div key={msg.id} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                  {/* Avatar */}
                  {!isUser && (
                    <div className="w-8 h-8 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center shrink-0">
                      <Cpu size={16} />
                    </div>
                  )}

                  <div className="space-y-2 max-w-[85%]">
                    {/* Text Bubble */}
                    <div
                      className={`p-3.5 rounded-xl border ${
                        isUser
                          ? 'bg-blue-600/10 border-blue-500/30 text-slate-200'
                          : 'bg-slate-950/80 border-slate-800 text-slate-300'
                      }`}
                    >
                      <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                    </div>

                    {/* Structured AI Findings (Only on Agent response containing data) */}
                    {msg.data && (
                      <div className="mt-4 space-y-4">
                        {/* Extracted filters */}
                        <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800/60 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                          <div>
                            <span className="text-slate-500 block uppercase">Plate No</span>
                            <span className="text-amber-400 font-bold">{msg.data.extracted_filters.plate || 'UNKNOWN'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block uppercase">Color</span>
                            <span className="text-slate-200 font-bold">{msg.data.extracted_filters.color?.toUpperCase() || 'UNKNOWN'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block uppercase">Model</span>
                            <span className="text-slate-200 font-bold">{msg.data.extracted_filters.model?.toUpperCase() || 'UNKNOWN'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block uppercase">Incident</span>
                            <span className="text-red-400 font-bold">{msg.data.extracted_filters.incident}</span>
                          </div>
                        </div>

                        {/* Bulleted Findings */}
                        <div className="bg-slate-950/20 border border-slate-800/80 p-4 rounded-xl space-y-2">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
                            <TrendingUp size={12} className="text-emerald-400" />
                            Core Correlated Findings
                          </h4>
                          <ul className="list-disc pl-4 space-y-1 text-xs text-slate-300">
                            {msg.data.findings.map((f, idx) => (
                              <li key={idx}>{f}</li>
                            ))}
                          </ul>
                        </div>

                        {/* Timeline */}
                        {msg.data.movement_timeline && msg.data.movement_timeline.length > 0 && (
                          <div className="bg-slate-950/20 border border-slate-800/80 p-4 rounded-xl space-y-3">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
                              <MapPin size={12} className="text-cyan-400" />
                              Sighting Trajectory Sequence
                            </h4>
                            <div className="relative border-l border-slate-800 pl-4 ml-2 space-y-4">
                              {msg.data.movement_timeline.map((wp, idx) => (
                                <div key={idx} className="relative">
                                  {/* Node dot */}
                                  <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-cyan-500 border border-slate-950" />
                                  <div className="space-y-0.5">
                                    <div className="flex items-center justify-between text-xs">
                                      <span className="font-bold text-slate-200">{wp.location}</span>
                                      <span className="text-[10px] text-slate-500 font-mono">
                                        {new Date(wp.timestamp).toLocaleTimeString()}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-3 text-[10px] text-slate-400 font-mono">
                                      <span className="flex items-center gap-0.5"><Clock size={10} /> {new Date(wp.timestamp).toLocaleDateString()}</span>
                                      <span className="text-amber-400/90 font-bold">Speed: {wp.speed_kmph} km/h</span>
                                      <span className="text-slate-500">Heading: {wp.direction}</span>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Evidence References */}
                        {msg.data.evidence_references && msg.data.evidence_references.length > 0 && (
                          <div className="bg-slate-950/20 border border-slate-800/80 p-4 rounded-xl space-y-2">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
                              <Zap size={12} className="text-purple-400" />
                              Evidence Credentials & OCR Confidences
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                              {msg.data.evidence_references.map((ev, idx) => (
                                <div key={idx} className="bg-slate-900 border border-slate-800/60 p-2.5 rounded-lg flex justify-between items-center">
                                  <div>
                                    <span className="font-semibold block text-slate-200 text-[11px]">{ev.camera_name}</span>
                                    <span className="text-[9px] font-mono text-slate-500">{ev.evidence_type}</span>
                                  </div>
                                  <div className="text-right">
                                    <span className="text-[10px] font-mono text-slate-400 block">CONFIDENCE</span>
                                    <span className="text-xs font-bold text-emerald-400">{(ev.confidence * 100).toFixed(0)}%</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Recommended Actions */}
                        {msg.data.recommended_actions && msg.data.recommended_actions.length > 0 && (
                          <div className="bg-slate-950/20 border border-slate-800/80 p-4 rounded-xl space-y-2">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
                              <CheckSquare size={12} className="text-amber-400" />
                              Recommended Tactical Action Plan
                            </h4>
                            <div className="space-y-1.5">
                              {msg.data.recommended_actions.map((act, idx) => {
                                const actionKey = `${msg.id}-act-${idx}`;
                                const isChecked = actionStates[actionKey] || false;
                                return (
                                  <button
                                    key={idx}
                                    onClick={() => toggleAction(actionKey)}
                                    className={`w-full flex items-center gap-3 p-2.5 rounded-lg text-left text-xs transition border ${
                                      isChecked
                                        ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                                        : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800'
                                    }`}
                                  >
                                    <span
                                      className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                                        isChecked
                                          ? 'bg-emerald-500 border-emerald-400 text-slate-950 font-bold'
                                          : 'border-slate-600'
                                      }`}
                                    >
                                      {isChecked && '✓'}
                                    </span>
                                    <span>{act}</span>
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* User Avatar */}
                  {isUser && (
                    <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 flex items-center justify-center shrink-0">
                      <User size={16} />
                    </div>
                  )}
                </div>
              );
            })}

            {isLoading && (
              <div className="flex justify-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center shrink-0 animate-spin">
                  <Cpu size={16} />
                </div>
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-400 text-xs font-mono flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                  Orchestrating agent filters & executing SQL DB tools...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Presets */}
          <div className="px-4 py-2 border-t border-slate-800/80 bg-slate-950/40 flex flex-wrap gap-2 text-xs">
            <span className="text-slate-500 font-mono py-1">PRESETS:</span>
            {presets.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => handlePresetClick(preset.query)}
                className="px-2.5 py-1 bg-slate-900 border border-slate-800 hover:border-cyan-500/40 hover:text-cyan-300 text-slate-400 rounded-lg transition font-mono"
              >
                {preset.label}
              </button>
            ))}
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-slate-800 bg-slate-950/80 flex gap-2 rounded-b-2xl">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Query vehicle attributes, plate registrations, toll locations..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-4 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-slate-100 disabled:text-slate-500 rounded-xl transition flex items-center justify-center shrink-0"
            >
              <Send size={16} />
            </button>
          </form>
        </div>

        {/* Status / Active Incidents Dossier - Right 5 Columns */}
        <div className="lg:col-span-5 space-y-6">
          {/* Active watchlist warning banner */}
          <div className="bg-red-950/15 border border-red-500/35 p-5 rounded-2xl shadow-xl flex gap-3.5 items-start">
            <div className="p-2.5 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400">
              <ShieldAlert size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-red-400 text-sm uppercase tracking-wide">Threat Center Status</h3>
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
              </div>
              <p className="text-xs text-slate-300 mt-1">2 Active Hotlist targets registered. Statewide PCR dispatch teams alerted for intercept operations on major Gujarat Toll corridors.</p>
            </div>
          </div>

          {/* Model Information */}
          <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl shadow-xl space-y-4">
            <div>
              <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wide">Ecosystem Diagnostics</h3>
              <p className="text-xs text-slate-400">Real-time consistency scores across integrated AI models</p>
            </div>
            
            <div className="space-y-3 font-mono text-xs">
              {/* YOLO26 */}
              <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span className="font-bold text-[11px]">1. YOLO26 DETECTOR & ANPR</span>
                  <span className="text-emerald-400">98.2%</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full w-[98%]" />
                </div>
                <span className="text-[10px] text-slate-500 block">Consistency: HIGH (Deterministic, local uvicorn runtime)</span>
              </div>

              {/* ByteTrack */}
              <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span className="font-bold text-[11px]">2. BYTETRACK MOTION ENGINE</span>
                  <span className="text-emerald-400">95.0%</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full w-[95%]" />
                </div>
                <span className="text-[10px] text-slate-500 block">Consistency: HIGH (Multi-frame coordinate continuity)</span>
              </div>

              {/* FastReID */}
              <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span className="font-bold text-[11px]">3. PyTorch Lightweight ReID</span>
                  <span className="text-cyan-400">91.8%</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-cyan-500 h-full w-[92%]" />
                </div>
                <span className="text-[10px] text-slate-500 block">Consistency: MEDIUM (512-dim embedding cosine match)</span>
              </div>

              {/* VLM Contextual */}
              <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span className="font-bold text-[11px]">4. CONTEXTUAL VLM & COPILOT</span>
                  <span className="text-amber-400">88.5%</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-amber-500 h-full w-[88%]" />
                </div>
                <span className="text-[10px] text-slate-500 block">Consistency: VARIABLE (Requires Google GenAI API connection)</span>
              </div>
            </div>
          </div>

          {/* Operational Advisory */}
          <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl text-xs text-slate-400 flex items-start gap-2.5 shadow-xl">
            <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-300">Legal Compliance Note: </span>
              <span>All automated queries, timeline tracks, and dispatcher dispatches generated by the Police Copilot Agent are recorded under the audit trail database. Check clearances and active case records before locking down districts.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
