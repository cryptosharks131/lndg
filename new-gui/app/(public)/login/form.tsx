'use client';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { login } from '@/app/auth/auth';
import Link from 'next/link';
import { useActionState } from 'react';


export function LoginForm() {
    const [state, action, pending] = useActionState(login, undefined);

    return (
        <form action={action} autoComplete='on'>
            <div className="flex flex-col gap-2">
                <div>
                    <Label htmlFor="username">User Name</Label>
                    <Input
                        id="username"
                        name="username"
                        placeholder="lndg-admin"
                        type="username"
                        defaultValue="lndg-admin"
                    />
                    {state?.errors?.username && (
                        <p className="text-sm text-red-500">{state.errors.username}</p>
                    )}
                </div>
                <div className="mt-4">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="password">Password</Label>

                    </div>
                    <Input id="password" type="password" name="password" />
                    {state?.errors?.password && (
                        <p className="text-sm text-red-500">{state.errors.password}</p>
                    )}
                </div>
                {state?.message && (
                    <p className="text-sm text-red-500">{state.message}</p>
                )}
                <Button aria-disabled={pending} type="submit" className="mt-4 w-full">
                    {pending ? 'Submitting...' : 'Sign in'}
                </Button>
            </div>
        </form>
    );
}
