import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTime(date: any): string {
  // 檢查日期是否有效，並確保是Date對象
  if (!date) {
    return '--:--'
  }
  
  // 如果不是Date對象，嘗試轉換
  let dateObj: Date
  if (date instanceof Date) {
    dateObj = date
  } else if (typeof date === 'string' || typeof date === 'number') {
    dateObj = new Date(date)
  } else {
    return '--:--'
  }
  
  // 檢查轉換後的日期是否有效
  if (isNaN(dateObj.getTime())) {
    return '--:--'
  }
  
  return new Intl.DateTimeFormat('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(dateObj)
}

export function formatDate(date: any): string {
  // 檢查日期是否有效，並確保是Date對象
  if (!date) {
    return '--'
  }
  
  // 如果不是Date對象，嘗試轉換
  let dateObj: Date
  if (date instanceof Date) {
    dateObj = date
  } else if (typeof date === 'string' || typeof date === 'number') {
    dateObj = new Date(date)
  } else {
    return '--'
  }
  
  // 檢查轉換後的日期是否有效
  if (isNaN(dateObj.getTime())) {
    return '--'
  }
  
  return new Intl.DateTimeFormat('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(dateObj)
}

export function generateId(): string {
  return Math.random().toString(36).substr(2, 9)
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substr(0, maxLength) + '...'
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(word => word.charAt(0))
    .join('')
    .toUpperCase()
    .substr(0, 2)
}
