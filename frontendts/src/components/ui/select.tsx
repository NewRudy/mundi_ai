import React from 'react'

// Minimal stub implementations to avoid external dependency while keeping API shape.
// These components render basic HTML elements and pass through children/props.

export const Select: React.FC<any> = ({ children, ...props }) => (
  <div data-ui-select {...props}>{children}</div>
)
export const SelectGroup: React.FC<any> = ({ children, ...props }) => (
  <div data-ui-select-group {...props}>{children}</div>
)
export const SelectValue: React.FC<any> = ({ children, ...props }) => (
  <span data-ui-select-value {...props}>{children}</span>
)
export const SelectTrigger: React.FC<any> = ({ children, ...props }) => (
  <button type="button" data-ui-select-trigger {...props}>{children}</button>
)
export const SelectContent: React.FC<any> = ({ children, ...props }) => (
  <div data-ui-select-content {...props}>{children}</div>
)
export const SelectLabel: React.FC<any> = ({ children, ...props }) => (
  <div data-ui-select-label {...props}>{children}</div>
)
export const SelectItem: React.FC<any> = ({ children, ...props }) => (
  <div role="option" data-ui-select-item {...props}>{children}</div>
)
export const SelectSeparator: React.FC<any> = (props) => (
  <hr data-ui-select-separator {...props} />
)

