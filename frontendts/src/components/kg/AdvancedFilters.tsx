import { Button } from '@/components/ui/button';
import { useCallback } from 'react';

export type Operator = 'contains' | 'equals' | 'gt' | 'lt';
export interface FilterCondition { key: string; op: Operator; value: string }

interface AdvancedFiltersProps {
  nodeConditions: FilterCondition[];
  setNodeConditions: (f: (prev: FilterCondition[]) => FilterCondition[]) => void;
  relConditions: FilterCondition[];
  setRelConditions: (f: (prev: FilterCondition[]) => FilterCondition[]) => void;
  relTypes: string[];
  selectedRelTypes: string[];
  setSelectedRelTypes: (vals: string[]) => void;
}

export default function AdvancedFilters({
  nodeConditions,
  setNodeConditions,
  relConditions,
  setRelConditions,
  relTypes,
  selectedRelTypes,
  setSelectedRelTypes,
}: AdvancedFiltersProps) {
  const toggleRelType = useCallback((t: string) => {
    setSelectedRelTypes(
      selectedRelTypes.includes(t)
        ? selectedRelTypes.filter((x) => x !== t)
        : [...selectedRelTypes, t]
    );
  }, [selectedRelTypes, setSelectedRelTypes]);

  return (
    <div className="space-y-3">
      <div>
        <div className="text-sm font-medium mb-1">Relationship types</div>
        <div className="flex flex-wrap gap-2">
          {relTypes.map((t) => (
            <button
              key={t}
              type="button"
              className={`text-xs px-2 py-1 rounded border ${selectedRelTypes.includes(t) ? 'bg-accent' : ''}`}
              onClick={() => toggleRelType(t)}
            >
              {t}
            </button>
          ))}
          {relTypes.length === 0 && (
            <div className="text-xs text-muted-foreground">No relationship types</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div className="text-sm font-medium mb-1">Node filters</div>
          <div className="flex flex-col gap-1">
            {nodeConditions.map((c, idx) => (
              <div key={idx} className="flex gap-1 items-center">
                <input className="w-28 border rounded px-1 py-0.5" placeholder="key" value={c.key} onChange={e => setNodeConditions(cs => cs.map((cc,i) => i===idx?{...cc,key:e.target.value}:cc))} />
                <select className="border rounded px-1 py-0.5" value={c.op} onChange={e => setNodeConditions(cs => cs.map((cc,i) => i===idx?{...cc,op:(e.target.value as Operator)}:cc))}>
                  <option value="contains">contains</option>
                  <option value="equals">equals</option>
                  <option value="gt">gt</option>
                  <option value="lt">lt</option>
                </select>
                <input className="w-32 border rounded px-1 py-0.5" placeholder="value" value={c.value} onChange={e => setNodeConditions(cs => cs.map((cc,i) => i===idx?{...cc,value:e.target.value}:cc))} />
                <Button size="sm" variant="outline" onClick={() => setNodeConditions(cs => cs.filter((_,i)=>i!==idx))}>X</Button>
              </div>
            ))}
            <Button size="sm" variant="outline" onClick={() => setNodeConditions(cs => [...cs, {key:'', op:'contains', value:''}])}>Add</Button>
          </div>
        </div>

        <div>
          <div className="text-sm font-medium mb-1">Relationship filters</div>
          <div className="flex flex-col gap-1">
            {relConditions.map((c, idx) => (
              <div key={idx} className="flex gap-1 items-center">
                <input className="w-28 border rounded px-1 py-0.5" placeholder="key" value={c.key} onChange={e => setRelConditions(cs => cs.map((cc,i) => i===idx?{...cc,key:e.target.value}:cc))} />
                <select className="border rounded px-1 py-0.5" value={c.op} onChange={e => setRelConditions(cs => cs.map((cc,i) => i===idx?{...cc,op:(e.target.value as Operator)}:cc))}>
                  <option value="contains">contains</option>
                  <option value="equals">equals</option>
                  <option value="gt">gt</option>
                  <option value="lt">lt</option>
                </select>
                <input className="w-32 border rounded px-1 py-0.5" placeholder="value" value={c.value} onChange={e => setRelConditions(cs => cs.map((cc,i) => i===idx?{...cc,value:e.target.value}:cc))} />
                <Button size="sm" variant="outline" onClick={() => setRelConditions(cs => cs.filter((_,i)=>i!==idx))}>X</Button>
              </div>
            ))}
            <Button size="sm" variant="outline" onClick={() => setRelConditions(cs => [...cs, {key:'', op:'contains', value:''}])}>Add</Button>
          </div>
        </div>
      </div>
    </div>
  );
}