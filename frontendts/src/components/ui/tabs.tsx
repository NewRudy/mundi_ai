import React from 'react'

// Minimal stub implementations to avoid external dependency while keeping API shape.
// These components render basic HTML elements and pass through children/props.

export const Tabs: React.FC<any> = ({ children, ...props }) => (
  <div data-ui-tabs {...props}>{children}</div>
)
export const TabsList: React.FC<any> = ({ children, ...props }) => (
  <div role="tablist" data-ui-tabs-list {...props}>{children}</div>
)
export const TabsTrigger: React.FC<any> = ({ children, ...props }) => (
  <button role="tab" type="button" data-ui-tabs-trigger {...props}>{children}</button>
)
export const TabsContent: React.FC<any> = ({ children, ...props }) => (
  <div role="tabpanel" data-ui-tabs-content {...props}>{children}</div>
)

