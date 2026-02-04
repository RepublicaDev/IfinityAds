/**
 * Componente Input - Base para inputs com acessibilidade
 */
import React from 'react'
import { cn } from '../design-system/tokens'

export function Input({
  label,
  id,
  type = 'text',
  placeholder,
  value,
  onChange,
  disabled = false,
  error,
  helperText,
  required = false,
  className,
  containerClassName,
  ...props
}) {
  const inputId = id || `input-${Math.random()}`

  return (
    <div className={cn('w-full', containerClassName)}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          {label}
          {required && <span className="text-red-600 ml-1" aria-label="required">*</span>}
        </label>
      )}
      
      <input
        id={inputId}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        disabled={disabled}
        required={required}
        aria-label={label || placeholder}
        aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
        className={cn(
          'w-full px-4 py-2 border rounded-lg',
          'text-gray-900 placeholder-gray-400',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
          'disabled:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-500',
          'transition-colors duration-200',
          error
            ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
            : 'border-gray-300',
          className
        )}
        {...props}
      />

      {error && (
        <p
          id={`${inputId}-error`}
          className="mt-1 text-sm text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}

      {helperText && !error && (
        <p
          id={`${inputId}-helper`}
          className="mt-1 text-sm text-gray-500"
        >
          {helperText}
        </p>
      )}
    </div>
  )
}

export default Input
