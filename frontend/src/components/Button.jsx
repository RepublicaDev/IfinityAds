/**
 * Componente Button - Base para todos os botões
 * Acessível, responsivo e componível
 */
import React from 'react'
import { cn } from '../design-system/tokens'

const buttonVariants = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 active:bg-gray-400',
  outline: 'border border-gray-300 text-gray-900 hover:bg-gray-50 active:bg-gray-100',
  ghost: 'text-blue-600 hover:bg-blue-50 active:bg-blue-100',
  danger: 'bg-red-600 text-white hover:bg-red-700 active:bg-red-800',
}

const buttonSizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
  xl: 'px-8 py-4 text-xl',
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  className,
  type = 'button',
  onClick,
  title,
  ...props
}) {
  const baseStyles = cn(
    'font-medium rounded-lg transition-colors duration-200',
    'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    'inline-flex items-center justify-center gap-2',
    buttonVariants[variant],
    buttonSizes[size],
    className
  )

  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={baseStyles}
      title={title}
      onClick={onClick}
      aria-busy={loading}
      {...props}
    >
      {loading && (
        <span
          className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  )
}

export default Button
