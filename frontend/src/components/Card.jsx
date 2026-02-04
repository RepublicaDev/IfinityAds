/**
 * Componente Card - Container base para conteúdo
 */
import React from 'react'
import { cn } from '../design-system/tokens'

export function Card({
  children,
  className,
  title,
  subtitle,
  footer,
  ...props
}) {
  return (
    <div
      className={cn(
        'bg-white rounded-lg border border-gray-200',
        'shadow-sm hover:shadow-md transition-shadow duration-200',
        className
      )}
      {...props}
    >
      {title && (
        <div className="border-b border-gray-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {subtitle && (
            <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
          )}
        </div>
      )}

      <div className="px-6 py-4">
        {children}
      </div>

      {footer && (
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 rounded-b-lg">
          {footer}
        </div>
      )}
    </div>
  )
}

export default Card
