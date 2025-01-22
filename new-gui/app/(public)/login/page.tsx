import { LoginForm } from "./form";
import Image from "next/image";

import { Zap } from "lucide-react";

export default function LoginPage() {
  return (
    <div className="grid min-h-svh lg:grid-cols-6">
      <div className="flex flex-col gap-4 p-6 md:p-10 col-span-2">
        <div className="flex justify-center gap-2 md:justify-start">
          <a href="#" className="flex items-center gap-2 font-medium">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Zap className="size-4" />
            </div>
            LNDg
          </a>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">
            <LoginForm />
          </div>
        </div>
      </div>
      <div className="relative hidden bg-muted lg:block col-span-4">
        <Image
          src="/LoginIMG.jpg"
          alt="Image showing a preview of the dashboard"
          height={500}
          width={500}
          className="absolute inset-0 h-full w-full object-cover dark:brightness-[0.9]"
        />
      </div>
    </div>
  );
}
