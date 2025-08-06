import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const isLoginPage = request.nextUrl.pathname === '/login';
  
  // 檢查 localStorage 中的 token
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    
    if (!token && !isLoginPage) {
      return NextResponse.redirect(new URL('/login', request.url));
    }

    if (token && isLoginPage) {
      return NextResponse.redirect(new URL('/summary', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/summary/:path*',
    '/admin/:path*',
    '/history/:path*',
    '/users/:path*',
    '/login'
  ]
};
