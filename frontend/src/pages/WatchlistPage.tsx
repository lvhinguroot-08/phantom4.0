import React, { useState, useMemo } from 'react';
import {
  Shield,
  ShieldAlert,
  Search,
  Plus,
  Filter,
  Trash2,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  Car,
  FileText,
  MapPin,
  X,
  Radio,
  Sparkles,
} from 'lucide-react';

interface WatchlistItem {
  id: string;
  plate: string;
  vehicle_model: string;
  vehicle_color: string;
  category: 'STOLEN' | 'WANTED' | 'BOLO' | 'REVOKED';
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  fir_number: string;
  district: string;
  reported_by: string;
  created_at: string;
  notes: string;
}

export const WatchlistPage: React.FC = () => {
  const [items, setItems] = useState<WatchlistItem[]>([
    {
      id: 'watch-001',
      plate: 'GJ 01 AB 1234',
      vehicle_model: 'Hyundai i20 (Silver)',
      vehicle_color: 'Silver',
      category: 'STOLEN',
      priority: 'CRITICAL',
      fir_number: 'FIR-492/2026',
      district: 'Ahmedabad',
      reported_by: 'Ahmedabad East Police Station',
      created_at: '2026-08-28',
      notes: 'Armed robbery suspect getaway vehicle. High-speed intercept authorized.',
    },
    {
      id: 'watch-002',
      plate: 'GJ 05 CD 5678',
      vehicle_model: 'Mahindra Scorpio (White)',
      vehicle_color: 'White',
      category: 'WANTED',
      priority: 'CRITICAL',
      fir_number: 'FIR-112/2026',
      district: 'Surat',
      reported_by: 'Surat Crime Branch',
      created_at: '2026-08-30',
      notes: 'Hit and run incident near Surat Ring Road junction.',
    },
    {
      id: 'watch-003',
      plate: 'GJ 11 XY 9012',
      vehicle_model: 'Tata 407 Truck (Yellow)',
      vehicle_color: 'Yellow',
      category: 'BOLO',
      priority: 'HIGH',
      fir_number: 'BOLO-784',
      district: 'Junagadh',
      reported_by: 'Junagadh Toll Gate Unit',
      created_at: '2026-08-31',
      notes: 'Carrying illicit commercial cargo through restricted wildlife corridor.',
    },
    {
      id: 'watch-004',
      plate: 'GJ 06 KL 3456',
      vehicle_model: 'Honda City (Black)',
      vehicle_color: 'Black',
      category: 'REVOKED',
      priority: 'MEDIUM',
      fir_number: 'RTO-REV-901',
      district: 'Vadodara',
      reported_by: 'Vadodara RTO Flying Squad',
      created_at: '2026-08-25',
      notes: 'Forged high-security registration plate and unpaid challans.',
    },
    {
      id: 'watch-005',
      plate: 'GJ 18 ZZ 8899',
      vehicle_model: 'Toyota Fortuner (Grey)',
      vehicle_color: 'Grey',
      category: 'WANTED',
      priority: 'CRITICAL',
      fir_number: 'FIR-884/2026',
      district: 'Gandhinagar',
      reported_by: 'Gandhinagar State Highway Patrol',
      created_at: '2026-09-01',
      notes: 'Fleeing checkpoint on SG Highway. Interceptor alert broadcasted.',
    },
  ]);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [districtFilter, setDistrictFilter] = useState<string>('ALL');
  const [showAddModal, setShowAddModal] = useState<boolean>(false);

  // Add Suspect Form
  const [newPlate, setNewPlate] = useState<string>('');
  const [newModel, setNewModel] = useState<string>('');
  const [newCategory, setNewCategory] = useState<'STOLEN' | 'WANTED' | 'BOLO' | 'REVOKED'>('STOLEN');
  const [newPriority, setNewPriority] = useState<'CRITICAL' | 'HIGH' | 'MEDIUM'>('CRITICAL');
  const [newFir, setNewFir] = useState<string>('');
  const [newDistrict, setNewDistrict] = useState<string>('Ahmedabad');
  const [newNotes, setNewNotes] = useState<string>('');

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (categoryFilter !== 'ALL' && item.category !== categoryFilter) return false;
      if (districtFilter !== 'ALL' && item.district !== districtFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().replace(/\s+/g, '');
        const plateNorm = item.plate.toLowerCase().replace(/\s+/g, '');
        if (
          !plateNorm.includes(q) &&
          !item.vehicle_model.toLowerCase().includes(q) &&
          !item.district.toLowerCase().includes(q) &&
          !item.fir_number.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [items, searchQuery, categoryFilter, districtFilter]);

  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlate.trim()) return;

    const newItem: WatchlistItem = {
      id: `watch-${Date.now()}`,
      plate: newPlate.toUpperCase(),
      vehicle_model: newModel || 'Unspecified Vehicle',
      vehicle_color: 'Various',
      category: newCategory,
      priority: newPriority,
      fir_number: newFir || 'FIR-PENDING',
      district: newDistrict,
      reported_by: 'State Command Center',
      created_at: new Date().toISOString().split('T')[0],
      notes: newNotes || 'Added by Command Operator',
    };

    setItems((prev) => [newItem, ...prev]);
    setShowAddModal(false);
    setNewPlate('');
    setNewModel('');
    setNewFir('');
    setNewNotes('');
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to remove this vehicle from the active Watchlist?')) {
      setItems((prev) => prev.filter((i) => i.id !== id));
    }
  };

  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner & Action Header */}
      <div
        style={{
          background: 'var(--glass-bg)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 24px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.45)',
              color: 'var(--accent-danger)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(239, 68, 68, 0.25)',
            }}
          >
            <ShieldAlert size={24} />
          </div>
          <div>
            <h1
              style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '1.3rem',
                fontWeight: 900,
                color: '#fff',
                letterSpacing: '1.5px',
                margin: 0,
              }}
            >
              STATEWIDE SUSPECT WATCHLIST & BOLO HOTLIST
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Real-time synchronization with Gujarat Police Crime Database & Automatic ANPR Interceptor Triggers
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="icon-btn highlight-btn"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 24px',
            height: 'auto',
            width: 'auto',
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, var(--accent-danger), #f97316)',
            border: 'none',
            color: '#fff',
            fontFamily: 'var(--font-heading)',
            fontSize: '0.88rem',
            fontWeight: 900,
            letterSpacing: '0.5px',
            cursor: 'pointer',
            boxShadow: '0 4px 18px rgba(239, 68, 68, 0.4)',
          }}
        >
          <Plus size={18} />
          <span>+ ADD SUSPECT VEHICLE</span>
        </button>
      </div>

      {/* High-Impact Search & Filter Bar */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(13, 21, 39, 0.9), rgba(19, 31, 56, 0.85))',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 22px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '300px' }}>
          <Search size={18} className="text-cyan" />
          <input
            type="text"
            placeholder="Search by Suspect Plate, Model, FIR Number, or District..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px 16px',
              color: '#fff',
              fontSize: '0.9rem',
              outline: 'none',
              fontFamily: 'var(--font-body)',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Category Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-primary)', padding: '8px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <Filter size={15} className="text-danger" />
            <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>CATEGORY:</span>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              style={{ background: 'transparent', color: '#fff', border: 'none', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
            >
              <option value="ALL" style={{ background: '#0a101d' }}>ALL CATEGORIES ({items.length})</option>
              <option value="STOLEN" style={{ background: '#0a101d' }}>STOLEN VEHICLES</option>
              <option value="WANTED" style={{ background: '#0a101d' }}>WANTED SUSPECTS</option>
              <option value="BOLO" style={{ background: '#0a101d' }}>BOLO ALERTS</option>
              <option value="REVOKED" style={{ background: '#0a101d' }}>REVOKED PERMITS</option>
            </select>
          </div>

          {/* District Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-primary)', padding: '8px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <MapPin size={15} className="text-cyan" />
            <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>DISTRICT:</span>
            <select
              value={districtFilter}
              onChange={(e) => setDistrictFilter(e.target.value)}
              style={{ background: 'transparent', color: '#fff', border: 'none', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
            >
              <option value="ALL" style={{ background: '#0a101d' }}>ALL DISTRICTS</option>
              <option value="Ahmedabad" style={{ background: '#0a101d' }}>Ahmedabad</option>
              <option value="Surat" style={{ background: '#0a101d' }}>Surat</option>
              <option value="Junagadh" style={{ background: '#0a101d' }}>Junagadh</option>
              <option value="Gandhinagar" style={{ background: '#0a101d' }}>Gandhinagar</option>
              <option value="Vadodara" style={{ background: '#0a101d' }}>Vadodara</option>
            </select>
          </div>
        </div>
      </div>

      {/* SCALED-UP ACTIVE WATCHLIST TABLE */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem', fontFamily: 'var(--font-body)' }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-medium)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
                <th style={{ padding: '16px 20px' }}>License Plate</th>
                <th style={{ padding: '16px 20px' }}>Category</th>
                <th style={{ padding: '16px 20px' }}>Vehicle Spec</th>
                <th style={{ padding: '16px 20px' }}>FIR / Case Ref</th>
                <th style={{ padding: '16px 20px' }}>District</th>
                <th style={{ padding: '16px 20px' }}>Investigator Notes</th>
                <th style={{ padding: '16px 20px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => (
                <tr
                  key={item.id}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* Plate Badge */}
                  <td style={{ padding: '16px 20px' }}>
                    <div
                      style={{
                        background: '#fef08a',
                        color: '#000',
                        border: '2px solid #000',
                        borderRadius: '4px',
                        padding: '4px 10px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 900,
                        fontSize: '0.95rem',
                        letterSpacing: '1.5px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                      }}
                    >
                      <span style={{ fontSize: '0.65rem', background: '#000', color: '#fff', padding: '1px 3px', borderRadius: '2px', fontWeight: 800 }}>IND</span>
                      <span>{item.plate}</span>
                    </div>
                  </td>

                  {/* Category Pill */}
                  <td style={{ padding: '16px 20px' }}>
                    <span
                      style={{
                        padding: '4px 10px',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 800,
                        fontSize: '0.75rem',
                        letterSpacing: '0.5px',
                        background:
                          item.category === 'STOLEN'
                            ? 'rgba(239, 68, 68, 0.2)'
                            : item.category === 'WANTED'
                            ? 'rgba(225, 29, 72, 0.2)'
                            : item.category === 'BOLO'
                            ? 'rgba(234, 179, 8, 0.2)'
                            : 'rgba(168, 85, 247, 0.2)',
                        border:
                          item.category === 'STOLEN'
                            ? '1px solid var(--accent-danger)'
                            : item.category === 'WANTED'
                            ? '1px solid #f43f5e'
                            : item.category === 'BOLO'
                            ? '1px solid var(--accent-attention)'
                            : '1px solid #c084fc',
                        color:
                          item.category === 'STOLEN'
                            ? 'var(--accent-danger)'
                            : item.category === 'WANTED'
                            ? '#fb7185'
                            : item.category === 'BOLO'
                            ? 'var(--accent-attention)'
                            : '#c084fc',
                      }}
                    >
                      {item.category}
                    </span>
                  </td>

                  {/* Vehicle Spec */}
                  <td style={{ padding: '16px 20px', color: '#fff', fontWeight: 700 }}>
                    {item.vehicle_model}
                  </td>

                  {/* FIR # */}
                  <td style={{ padding: '16px 20px', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontWeight: 700, fontSize: '0.82rem' }}>
                    {item.fir_number}
                  </td>

                  {/* District */}
                  <td style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>
                    {item.district}
                  </td>

                  {/* Notes */}
                  <td style={{ padding: '16px 20px', color: 'var(--text-muted)', fontSize: '0.8rem', maxWidth: '300px' }}>
                    {item.notes}
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '16px 20px', textAlign: 'right' }}>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="icon-btn"
                      style={{
                        padding: '6px 12px',
                        height: 'auto',
                        width: 'auto',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--accent-danger)',
                        borderColor: 'rgba(239, 68, 68, 0.4)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        fontSize: '0.75rem',
                      }}
                      title="Remove from Watchlist"
                    >
                      <Trash2 size={14} />
                      <span>REMOVE</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Suspect Vehicle Modal */}
      {showAddModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: 'rgba(0, 0, 0, 0.88)',
            backdropFilter: 'blur(12px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-lg)',
              width: '100%',
              maxWidth: '650px',
              padding: '24px',
              boxShadow: 'var(--shadow-3d)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldAlert size={22} className="text-danger" />
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                  ADD SUSPECT VEHICLE TO WATCHLIST
                </h2>
              </div>
              <button onClick={() => setShowAddModal(false)} className="icon-btn" style={{ width: '32px', height: '32px' }}>
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleAddSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>LICENSE PLATE *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. GJ 01 AB 1234"
                    value={newPlate}
                    onChange={(e) => setNewPlate(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none', fontFamily: 'var(--font-mono)', fontWeight: 800, textTransform: 'uppercase' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>VEHICLE MAKE / MODEL</label>
                  <input
                    type="text"
                    placeholder="e.g. White Mahindra Scorpio"
                    value={newModel}
                    onChange={(e) => setNewModel(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>WATCHLIST CATEGORY</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value as any)}
                    style={{ width: '100%', padding: '10px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none', fontFamily: 'var(--font-mono)' }}
                  >
                    <option value="STOLEN">STOLEN VEHICLE</option>
                    <option value="WANTED">WANTED FELON</option>
                    <option value="BOLO">BOLO (BE ON THE LOOKOUT)</option>
                    <option value="REVOKED">REVOKED PERMIT</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>PRIMARY DISTRICT</label>
                  <select
                    value={newDistrict}
                    onChange={(e) => setNewDistrict(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none' }}
                  >
                    <option value="Ahmedabad">Ahmedabad</option>
                    <option value="Surat">Surat</option>
                    <option value="Junagadh">Junagadh</option>
                    <option value="Gandhinagar">Gandhinagar</option>
                    <option value="Vadodara">Vadodara</option>
                    <option value="Rajkot">Rajkot</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>FIR / CASE NUMBER</label>
                <input
                  type="text"
                  placeholder="e.g. FIR #492/2026 (Ahmedabad East)"
                  value={newFir}
                  onChange={(e) => setNewFir(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>INVESTIGATION NOTES / REASON FOR HOTLIST</label>
                <textarea
                  rows={3}
                  placeholder="Provide incident details, suspect descriptions, and dispatch protocols..."
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none', resize: 'none' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" onClick={() => setShowAddModal(false)} className="icon-btn" style={{ padding: '10px 20px', width: 'auto', height: 'auto' }}>
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="icon-btn highlight-btn"
                  style={{
                    padding: '10px 24px',
                    width: 'auto',
                    height: 'auto',
                    background: 'linear-gradient(135deg, var(--accent-danger), #f97316)',
                    color: '#fff',
                    fontWeight: 900,
                    border: 'none',
                  }}
                >
                  ADD TO HOTLIST
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
