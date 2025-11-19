/**
 * ViewModeToggle - 2D/3D视图切换MapLibre控件
 * 弹出式选择器设计：点击按钮后弹出菜单显示三种模式选项
 */

import { useEffect, useRef, useCallback } from 'react';
import { useUnifiedView } from '@/contexts/UnifiedViewContext';
import { toast } from 'sonner';

// MapLibre控件类 - 弹出式设计
class ViewModeToggleControl {
  private container: HTMLElement;
  private mainButton: HTMLButtonElement | null = null;
  private dropdownMenu: HTMLElement | null = null;
  private onModeChange: (mode: '2d' | '3d' | 'split') => void;
  private currentMode: '2d' | '3d' | 'split';

  constructor(onModeChange: (mode: '2d' | '3d' | 'split') => void, currentMode: '2d' | '3d' | 'split') {
    this.onModeChange = onModeChange;
    this.currentMode = currentMode;

    this.container = document.createElement('div');
    this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group view-mode-toggle-popup';

    this.createUI();
    this.bindEvents();
  }

  private createUI() {
    // 创建主按钮
    this.mainButton = document.createElement('button');
    this.mainButton.className = 'maplibregl-ctrl-icon main-toggle-btn';
    this.mainButton.type = 'button';
    this.mainButton.title = this.getCurrentModeTitle();

    const iconDiv = document.createElement('div');
    iconDiv.className = 'current-mode-icon';
    iconDiv.innerHTML = this.getCurrentModeIcon();
    this.mainButton.appendChild(iconDiv);

    this.mainButton.appendChild(iconDiv);

    this.container.appendChild(this.mainButton);

    // 创建下拉菜单（初始隐藏）
    this.dropdownMenu = document.createElement('div');
    this.dropdownMenu.className = 'view-mode-dropdown';
    this.dropdownMenu.style.display = 'none';

    // 创建菜单项
    const modes: Array<{ id: '2d' | '3d' | 'split', label: string, icon: string }> = [
      { id: '2d', label: '2D地图', icon: this.getModeIcon('2d') },
      { id: '3d', label: '3D场景', icon: this.getModeIcon('3d') },
      { id: 'split', label: '分屏', icon: this.getModeIcon('split') }
    ];

    modes.forEach(mode => {
      const menuItem = document.createElement('div');
      menuItem.className = 'dropdown-menu-item';
      menuItem.dataset.mode = mode.id;

      if (mode.id === this.currentMode) {
        menuItem.classList.add('active');
      }

      const iconSpan = document.createElement('span');
      iconSpan.className = 'menu-item-icon';
      iconSpan.innerHTML = mode.icon;
      menuItem.appendChild(iconSpan);

      const labelSpan = document.createElement('span');
      labelSpan.className = 'menu-item-label';
      labelSpan.textContent = mode.label;
      menuItem.appendChild(labelSpan);

      this.dropdownMenu.appendChild(menuItem);
    });

    this.container.appendChild(this.dropdownMenu);
  }

  private bindEvents() {
    // 主按钮点击事件
    this.mainButton?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleDropdown();
    });

    // 菜单项点击事件
    this.dropdownMenu?.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      const menuItem = target.closest('.dropdown-menu-item') as HTMLElement;

      if (!menuItem) return;

      e.stopPropagation();

      const mode = menuItem.dataset.mode as '2d' | '3d' | 'split';

      this.selectMode(mode);
    });

    // 点击其他地方关闭下拉菜单
    document.addEventListener('click', () => {
      this.hideDropdown();
    });

    // 点击容器内其他地方不关闭
    this.container.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }

  private toggleDropdown() {
    if (!this.dropdownMenu) return;

    if (this.dropdownMenu.style.display === 'none') {
      this.showDropdown();
    } else {
      this.hideDropdown();
    }
  }

  private showDropdown() {
    if (!this.dropdownMenu) return;

    this.dropdownMenu.style.display = 'block';
    this.container.classList.add('dropdown-open');
  }

  private hideDropdown() {
    if (!this.dropdownMenu) return;

    this.dropdownMenu.style.display = 'none';
    this.container.classList.remove('dropdown-open');
  }

  private selectMode(mode: '2d' | '3d' | 'split') {
    this.currentMode = mode;

    // 触发回调
    this.onModeChange(mode);

    // 更新UI
    this.updateButtonUI(mode);
    this.updateMenuUI(mode);

    // 隐藏下拉菜单
    this.hideDropdown();
  }

  private updateButtonUI(mode: '2d' | '3d' | 'split') {
    if (!this.mainButton) return;

    // 更新图标
    const iconDiv = this.mainButton.querySelector('.current-mode-icon') as HTMLElement;
    if (iconDiv) {
      iconDiv.innerHTML = this.getModeIcon(mode);
    }

    // 更新标题
    this.mainButton.title = this.getModeTitle(mode);
  }

  private updateMenuUI(mode: '2d' | '3d' | 'split') {
    if (!this.dropdownMenu) return;

    const items = this.dropdownMenu.querySelectorAll('.dropdown-menu-item');
    items.forEach(item => {
      item.classList.remove('active');
      if (item.dataset.mode === mode) {
        item.classList.add('active');
      }
    });
  }

  private getCurrentModeTitle(): string {
    return this.getModeTitle(this.currentMode);
  }

  private getCurrentModeLabel(): string {
    return this.getModeLabel(this.currentMode);
  }

  private getCurrentModeIcon(): string {
    return this.getModeIcon(this.currentMode);
  }

  private getModeTitle(mode: '2d' | '3d' | 'split'): string {
    switch (mode) {
      case '2d': return '2D地图视图 - 点击切换';
      case '3d': return '3D场景视图 - 点击切换';
      case 'split': return '分屏显示（2D+3D） - 点击切换';
    }
  }

  private getModeLabel(mode: '2d' | '3d' | 'split'): string {
    switch (mode) {
      case '2d': return '2D';
      case '3d': return '3D';
      case 'split': return '分屏';
    }
  }

  private getModeIcon(mode: '2d' | '3d' | 'split'): string {
    switch (mode) {
      case '2d':
        return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/><path d="M15 6v12"/></svg>';
      case '3d':
        return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>';
      case 'split':
        return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="8" height="18" rx="2"/><rect x="13" y="3" width="8" height="18" rx="2"/></svg>';
    }
  }

  setMode(mode: '2d' | '3d' | 'split') {
    this.currentMode = mode;
    this.updateButtonUI(mode);
    this.updateMenuUI(mode);
  }

  onAdd(map: any): HTMLElement {
    return this.container;
  }

  onRemove(): void {
    if (this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
  }

  getDefaultPosition(): string {
    return 'top-right';
  }
}

// React Hook - 用于在组件中初始化控件
export function useViewModeToggle(map: any) {
  const { viewMode, setViewMode } = useUnifiedView();
  const controlRef = useRef<any>(null);

  const handleModeChange = useCallback((mode: '2d' | '3d' | 'split') => {
    setViewMode(mode);

    // 显示提示
    const modeNames = {
      '2d': '2D地图视图',
      '3d': '3D场景视图',
      'split': '分屏显示'
    };
    toast.success(`已切换到${modeNames[mode]}`);
  }, [setViewMode]);

  useEffect(() => {
    if (!map) return;

    // 创建控件
    controlRef.current = new ViewModeToggleControl(handleModeChange, viewMode);

    // 添加到地图
    map.addControl(controlRef.current, 'top-right');

    return () => {
      if (map && controlRef.current) {
        map.removeControl(controlRef.current);
      }
    };
  }, [map, handleModeChange, viewMode]);

  // 更新按钮状态当viewMode改变时
  useEffect(() => {
    if (controlRef.current) {
      controlRef.current.setMode(viewMode);
    }
  }, [viewMode]);

  return controlRef.current;
}

// 组件（向后兼容）
export function ViewModeToggle() {
  return null; // 组件不直接渲染，通过hooks使用
}

export default ViewModeToggle;

// 添加CSS样式
const style = document.createElement('style');
style.textContent = `
  .view-mode-toggle-popup {
    position: relative;
    overflow: visible !important; /* Ensure dropdown can be seen */
  }

  .view-mode-toggle-popup .maplibregl-ctrl-icon.main-toggle-btn {
    width: 29px !important;
    height: 29px !important;
    min-width: unset !important;
    border: none;
    background-color: #fff;
    cursor: pointer;
    display: flex !important;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: background-color 0.2s ease;
    outline: none;
  }

  .view-mode-toggle-popup .maplibregl-ctrl-icon.main-toggle-btn:hover {
    background-color: #f0f0f0;
  }

  .view-mode-toggle-popup .current-mode-icon {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #333;
  }

  .view-mode-toggle-popup .current-mode-icon svg {
    width: 100%;
    height: 100%;
  }

  .view-mode-dropdown {
    position: absolute;
    top: 0;
    right: 35px; /* Position to the left of the button */
    background: #fff;
    border-radius: 4px;
    box-shadow: 0 0 0 2px rgba(0,0,0,0.1);
    min-width: 140px;
    overflow: hidden;
    z-index: 9999;
    display: none; /* Default hidden */
    animation: fadeIn 0.2s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateX(5px); }
    to { opacity: 1; transform: translateX(0); }
  }

  .view-mode-toggle-popup.dropdown-open .view-mode-dropdown {
    display: block !important;
  }

  .dropdown-menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    border-bottom: 1px solid #f0f0f0;
    font-size: 13px;
    color: #333;
  }

  .dropdown-menu-item:last-child {
    border-bottom: none;
  }

  .dropdown-menu-item:hover {
    background-color: #f9fafb;
  }

  .dropdown-menu-item.active {
    background-color: #eff6ff;
    color: #2563eb;
    font-weight: 500;
  }

  .dropdown-menu-item.active .menu-item-icon {
    color: #2563eb;
  }

  .menu-item-icon {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #666;
  }

  .menu-item-icon svg {
    width: 100%;
    height: 100%;
  }

  .menu-item-label {
    flex: 1;
  }
`;
document.head.appendChild(style);
