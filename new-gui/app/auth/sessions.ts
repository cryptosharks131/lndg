import 'server-only'

import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

import type { SessionPayload } from '@/app/auth/definitions'
import { jwtDecode } from '@/lib/utils';

const API_URL = process.env.API_URL;

export async function createSession(sessionPayload: SessionPayload) {
    
    
    const decoded = jwtDecode(sessionPayload.accessToken); 

    const expiresAt:number = decoded.exp * 1000;

        // Set tokens as HTTP-only cookies
        (await cookies()).set('accessToken', sessionPayload.accessToken, {
            httpOnly: true,
            secure: true,
            expires: expiresAt,
            sameSite: 'lax',
            path: '/',});
        (await cookies()).set('refreshToken', sessionPayload.refreshToken, { 
            httpOnly: true,
            secure: true,
            expires: expiresAt,
            sameSite: 'lax',
            path: '/', });
        
      redirect('/dashboard');
    }



export async function refreshSession () {
    const refreshToken = (await cookies()).get('refreshToken')?.value;
    // console.log(refreshToken)


    const res = await fetch(`${API_URL}/api/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });


      if (!res.ok) {
        throw new Error('Failed to refresh token');
      }
    
      const { access } = await res.json();

    const decoded = jwtDecode(access); 
    
    const expiresAt:number = decoded.exp * 1000;
    
      // Update the access token in cookies
      
      (await cookies()).set('accessToken', access, {           
        httpOnly: true,
        secure: true,
        expires: expiresAt,
        sameSite: 'lax',
        path: '/',});
       
        if (refreshToken) {
            (await cookies()).set('refreshToken', refreshToken, {           
                httpOnly: true,
                secure: true,
                expires: expiresAt,
                sameSite: 'lax',
                path: '/',});
        } else {
            console.log("refresh token not found")
        }
                
      return { success: true };

}    

export async function verifySession() {
    const accessToken = (await cookies()).get('accessToken')?.value
    
    if (!accessToken) {
        redirect('/login')
    }

    return { isAuth: true, accessToken: accessToken  };
}


export async function deleteSession() {

    const cookieStore = await cookies()
    cookieStore.delete('accessToken')
    cookieStore.delete('refreshToken')

}