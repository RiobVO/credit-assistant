"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthError, login } from "@/lib/auth";
import { cn } from "@/lib/utils";

const schema = z.object({
  email: z.string().min(3, "Введите email").max(255),
  password: z.string().min(1, "Введите пароль").max(200),
});

type FormValues = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const nextPath = params.get("next") ?? "/search";

  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await login(values);
      router.push(nextPath);
      router.refresh();
    } catch (e) {
      if (e instanceof AuthError && e.status === 401) {
        setServerError("Неверный email или пароль");
      } else {
        setServerError("Не удалось войти. Попробуйте ещё раз.");
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <Field label="Email" htmlFor="email" error={errors.email?.message}>
        <input
          id="email"
          type="email"
          autoComplete="email"
          autoFocus
          {...register("email")}
          className="w-full rounded-md border border-[#283B5F] bg-[#162038] px-3 py-2 text-[13.5px] text-[#F2F4F8] placeholder-[#5E6E89] outline-none transition focus:border-[#4A7BD9] focus:ring-1 focus:ring-[#4A7BD9]/40"
          placeholder="ivanov@bank.uz"
          disabled={isSubmitting}
        />
      </Field>

      <Field label="Пароль" htmlFor="password" error={errors.password?.message}>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
          className="w-full rounded-md border border-[#283B5F] bg-[#162038] px-3 py-2 text-[13.5px] text-[#F2F4F8] placeholder-[#5E6E89] outline-none transition focus:border-[#4A7BD9] focus:ring-1 focus:ring-[#4A7BD9]/40"
          placeholder="••••••••"
          disabled={isSubmitting}
        />
      </Field>

      {serverError && (
        <div
          role="alert"
          className="rounded-md border border-[#5C2B2E] bg-[#2A1215] px-3 py-2 text-[12.5px] text-[#FFB4AB]"
        >
          {serverError}
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className={cn(
          "mt-2 w-full rounded-md bg-[#1E40AF] px-3 py-2.5 text-[13.5px] font-semibold text-white transition hover:bg-[#1A3899]",
          "disabled:cursor-wait disabled:opacity-70",
        )}
      >
        {isSubmitting ? "Входим…" : "Войти"}
      </button>
    </form>
  );
}

function Field({
  label,
  htmlFor,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-[12px] font-medium text-[#C5CCDA]"
      >
        {label}
      </label>
      {children}
      {error && (
        <p className="mt-1 text-[11.5px] text-[#FFB4AB]" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
