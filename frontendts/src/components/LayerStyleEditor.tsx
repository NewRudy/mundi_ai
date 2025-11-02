import { useMutation, useQuery } from '@tanstack/react-query';
import { Palette, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import type { MapLayer } from '../lib/types';

interface LayerStyleEditorProps {
  layer: MapLayer;
  mapId: string;
  onClose: () => void;
  onUpdate: () => void;
}

interface LayerStyle {
  color?: string;
  fillColor?: string;
  fillOpacity?: number;
  lineColor?: string;
  lineWidth?: number;
  lineOpacity?: number;
  circleRadius?: number;
  circleColor?: string;
  circleOpacity?: number;
  circleStrokeColor?: string;
  circleStrokeWidth?: number;
}

export default function LayerStyleEditor({ layer, mapId, onClose, onUpdate }: LayerStyleEditorProps) {
  const [style, setStyle] = useState<LayerStyle>({
    fillColor: '#3b82f6',
    fillOpacity: 0.6,
    lineColor: '#1e40af',
    lineWidth: 2,
    lineOpacity: 1,
    circleRadius: 6,
    circleColor: '#3b82f6',
    circleOpacity: 0.8,
    circleStrokeColor: '#ffffff',
    circleStrokeWidth: 1,
  });

  const [layerType, setLayerType] = useState<'fill' | 'line' | 'circle'>('fill');

  // Fetch current style.json to prefill existing style values if present
  const { data: currentStyle } = useQuery({
    queryKey: ['mapStyle', mapId, 'editor-prefill'],
    queryFn: async () => {
      const res = await fetch(`/api/maps/${mapId}/style.json`);
      if (!res.ok) throw new Error('Failed to fetch style.json');
      return (await res.json()) as any;
    },
    enabled: !!mapId,
  });

  // Determine preferred layer type from existing style or layer metadata
  const inferredLayerType = useMemo(() => {
    // Prefer existing style layer if available
    const layers: any[] = currentStyle?.layers || [];
    const forSource = layers.filter((l) => l.source === layer.id);
    const firstFill = forSource.find((l) => l.type === 'fill');
    const firstLine = forSource.find((l) => l.type === 'line');
    const firstCircle = forSource.find((l) => l.type === 'circle');
    if (firstFill) return 'fill' as const;
    if (firstLine) return 'line' as const;
    if (firstCircle) return 'circle' as const;
    // Fall back to geometry inference
    if (layer.type === 'point_cloud') return 'circle' as const;
    if (layer.metadata?.geometry_type === 'Point') return 'circle' as const;
    if (layer.metadata?.geometry_type === 'LineString' || layer.metadata?.geometry_type === 'MultiLineString') return 'line' as const;
    return 'fill' as const;
  }, [currentStyle, layer]);

  useEffect(() => {
    setLayerType(inferredLayerType);
  }, [inferredLayerType]);

  const updateStyleMutation = useMutation({
    mutationFn: async (newStyle: LayerStyle) => {
      // Build MapLibre GL layers payload according to selected layerType
      const layers: any[] = [];
      if (layerType === 'fill') {
        layers.push({
          id: `${layer.id}-fill`,
          type: 'fill',
          source: layer.id,
          'source-layer': 'reprojectedfgb',
          paint: {
            'fill-color': newStyle.fillColor || '#3b82f6',
            'fill-opacity': newStyle.fillOpacity ?? 0.6,
            ...(newStyle.lineColor ? { 'fill-outline-color': newStyle.lineColor } : {}),
          },
        });
      } else if (layerType === 'line') {
        layers.push({
          id: `${layer.id}-line`,
          type: 'line',
          source: layer.id,
          'source-layer': 'reprojectedfgb',
          paint: {
            'line-color': newStyle.lineColor || '#1e40af',
            'line-width': newStyle.lineWidth ?? 2,
            'line-opacity': newStyle.lineOpacity ?? 1,
          },
        });
      } else if (layerType === 'circle') {
        layers.push({
          id: `${layer.id}-circle`,
          type: 'circle',
          source: layer.id,
          'source-layer': 'reprojectedfgb',
          paint: {
            'circle-color': newStyle.circleColor || '#3b82f6',
            'circle-radius': newStyle.circleRadius ?? 6,
            'circle-opacity': newStyle.circleOpacity ?? 0.8,
            ...(newStyle.circleStrokeColor ? { 'circle-stroke-color': newStyle.circleStrokeColor } : {}),
            ...(newStyle.circleStrokeWidth !== undefined ? { 'circle-stroke-width': newStyle.circleStrokeWidth } : {}),
          },
        });
      }

      const response = await fetch(`/api/layers/${layer.id}/style`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ maplibre_json_layers: layers, map_id: mapId }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Failed to update style');
      }

      return response.json();
    },
    onSuccess: () => {
      toast.success('Layer style updated successfully');
      onUpdate();
    },
    onError: (error: Error) => {
      toast.error(`Failed to update style: ${error.message}`);
    },
  });

  const handleApply = () => {
    updateStyleMutation.mutate(style);
  };

  // Prefill from existing style if available
  useEffect(() => {
    const layers = (currentStyle?.layers || []) as any[];
    const bySource = layers.filter((l) => l.source === layer.id);
    const l = bySource.find((x) => x.type === 'fill') || bySource.find((x) => x.type === 'line') || bySource.find((x) => x.type === 'circle');
    if (!l) return;
    if (l.type === 'fill') {
      setStyle((prev) => ({
        ...prev,
        fillColor: l.paint?.['fill-color'] ?? prev.fillColor,
        fillOpacity: l.paint?.['fill-opacity'] ?? prev.fillOpacity,
        lineColor: l.paint?.['fill-outline-color'] ?? prev.lineColor,
      }));
    } else if (l.type === 'line') {
      setStyle((prev) => ({
        ...prev,
        lineColor: l.paint?.['line-color'] ?? prev.lineColor,
        lineWidth: l.paint?.['line-width'] ?? prev.lineWidth,
        lineOpacity: l.paint?.['line-opacity'] ?? prev.lineOpacity,
      }));
    } else if (l.type === 'circle') {
      setStyle((prev) => ({
        ...prev,
        circleColor: l.paint?.['circle-color'] ?? prev.circleColor,
        circleRadius: l.paint?.['circle-radius'] ?? prev.circleRadius,
        circleOpacity: l.paint?.['circle-opacity'] ?? prev.circleOpacity,
        circleStrokeColor: l.paint?.['circle-stroke-color'] ?? prev.circleStrokeColor,
        circleStrokeWidth: l.paint?.['circle-stroke-width'] ?? prev.circleStrokeWidth,
      }));
    }
  }, [currentStyle, layer.id]);

  return (
    <Card className="w-80 shadow-lg">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Palette className="w-4 h-4" />
            Style Editor
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-6 w-6 p-0">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground truncate" title={layer.name}>
          {layer.name}
        </p>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {/* Layer Type Selector */}
        <div className="space-y-2">
          <Label>Layer Type</Label>
          <Select value={layerType} onValueChange={(v: string) => setLayerType(v as 'fill' | 'line' | 'circle')}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="fill">Polygon (Fill)</SelectItem>
              <SelectItem value="line">Line</SelectItem>
              <SelectItem value="circle">Point (Circle)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Fill Styles */}
        {layerType === 'fill' && (
          <>
            <div className="space-y-2">
              <Label>Fill Color</Label>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={style.fillColor}
                  onChange={(e) => setStyle({ ...style, fillColor: e.target.value })}
                  className="w-16 h-9 p-1"
                />
                <Input
                  type="text"
                  value={style.fillColor}
                  onChange={(e) => setStyle({ ...style, fillColor: e.target.value })}
                  className="flex-1"
                  placeholder="#3b82f6"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Fill Opacity: {style.fillOpacity?.toFixed(2)}</Label>
              <Slider
                value={[style.fillOpacity || 0.6]}
                onValueChange={(vals: number[]) => setStyle({ ...style, fillOpacity: vals[0] })}
                min={0}
                max={1}
                step={0.05}
              />
            </div>
            <div className="space-y-2">
              <Label>Stroke Color</Label>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={style.lineColor}
                  onChange={(e) => setStyle({ ...style, lineColor: e.target.value })}
                  className="w-16 h-9 p-1"
                />
                <Input
                  type="text"
                  value={style.lineColor}
                  onChange={(e) => setStyle({ ...style, lineColor: e.target.value })}
                  className="flex-1"
                  placeholder="#1e40af"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Stroke Width: {style.lineWidth}px</Label>
              <Slider
                value={[style.lineWidth || 2]}
                onValueChange={(vals: number[]) => setStyle({ ...style, lineWidth: vals[0] })}
                min={0}
                max={10}
                step={0.5}
              />
            </div>
          </>
        )}

        {/* Line Styles */}
        {layerType === 'line' && (
          <>
            <div className="space-y-2">
              <Label>Line Color</Label>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={style.lineColor}
                  onChange={(e) => setStyle({ ...style, lineColor: e.target.value })}
                  className="w-16 h-9 p-1"
                />
                <Input
                  type="text"
                  value={style.lineColor}
                  onChange={(e) => setStyle({ ...style, lineColor: e.target.value })}
                  className="flex-1"
                  placeholder="#1e40af"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Line Width: {style.lineWidth}px</Label>
              <Slider
                value={[style.lineWidth || 2]}
                onValueChange={(vals: number[]) => setStyle({ ...style, lineWidth: vals[0] })}
                min={0.5}
                max={20}
                step={0.5}
              />
            </div>
            <div className="space-y-2">
              <Label>Line Opacity: {style.lineOpacity?.toFixed(2)}</Label>
              <Slider
                value={[style.lineOpacity || 1]}
                onValueChange={(vals: number[]) => setStyle({ ...style, lineOpacity: vals[0] })}
                min={0}
                max={1}
                step={0.05}
              />
            </div>
          </>
        )}

        {/* Circle Styles */}
        {layerType === 'circle' && (
          <>
            <div className="space-y-2">
              <Label>Circle Radius: {style.circleRadius}px</Label>
              <Slider
                value={[style.circleRadius || 6]}
                onValueChange={(vals: number[]) => setStyle({ ...style, circleRadius: vals[0] })}
                min={1}
                max={30}
                step={1}
              />
            </div>
            <div className="space-y-2">
              <Label>Circle Color</Label>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={style.circleColor}
                  onChange={(e) => setStyle({ ...style, circleColor: e.target.value })}
                  className="w-16 h-9 p-1"
                />
                <Input
                  type="text"
                  value={style.circleColor}
                  onChange={(e) => setStyle({ ...style, circleColor: e.target.value })}
                  className="flex-1"
                  placeholder="#3b82f6"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Circle Opacity: {style.circleOpacity?.toFixed(2)}</Label>
              <Slider
                value={[style.circleOpacity || 0.8]}
                onValueChange={(vals: number[]) => setStyle({ ...style, circleOpacity: vals[0] })}
                min={0}
                max={1}
                step={0.05}
              />
            </div>
            <div className="space-y-2">
              <Label>Stroke Color</Label>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={style.circleStrokeColor}
                  onChange={(e) => setStyle({ ...style, circleStrokeColor: e.target.value })}
                  className="w-16 h-9 p-1"
                />
                <Input
                  type="text"
                  value={style.circleStrokeColor}
                  onChange={(e) => setStyle({ ...style, circleStrokeColor: e.target.value })}
                  className="flex-1"
                  placeholder="#ffffff"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Stroke Width: {style.circleStrokeWidth}px</Label>
              <Slider
                value={[style.circleStrokeWidth || 1]}
                onValueChange={(vals: number[]) => setStyle({ ...style, circleStrokeWidth: vals[0] })}
                min={0}
                max={10}
                step={0.5}
              />
            </div>
          </>
        )}

        <div className="flex gap-2 pt-2">
          <Button onClick={handleApply} disabled={updateStyleMutation.isPending} className="flex-1">
            {updateStyleMutation.isPending ? 'Applying...' : 'Apply'}
          </Button>
          <Button variant="outline" onClick={onClose} className="flex-1">
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
