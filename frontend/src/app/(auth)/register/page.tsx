"use client";

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema, type RegisterFormData } from "@/lib/validations";
import { useAuth } from "@/hooks/use-auth";
import { authApi } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  Loader2,
  Eye,
  EyeOff,
  Check,
  X,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

export default function RegisterPage() {
  const { register: registerUser, isRegistering } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [usernameStatus, setUsernameStatus] = useState<{
    checking: boolean;
    available: boolean | null;
    message: string;
  }>({ checking: false, available: null, message: "" });

  const form = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      username: "",
      password: "",
      confirmPassword: "",
      first_name: "",
      last_name: "",
    },
    mode: "onChange",
  });

  const password = form.watch("password");
  const username = form.watch("username");

  // Password strength indicators
  const passwordChecks = [
    { label: "Greater than 8 characters", met: password.length > 8 },
    { label: "1 uppercase letter", met: /[A-Z]/.test(password) },
    { label: "1 lowercase letter", met: /[a-z]/.test(password) },
    { label: "1 number", met: /[0-9]/.test(password) },
    {
      label: "1 special character",
      met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password),
    },
  ];

  // Debounced username availability check
  const checkUsername = useCallback(async (value: string) => {
    if (value.length < 5) {
      setUsernameStatus({ checking: false, available: null, message: "" });
      return;
    }
    if (!/^[a-zA-Z0-9_]+$/.test(value)) {
      setUsernameStatus({ checking: false, available: null, message: "" });
      return;
    }

    setUsernameStatus({ checking: true, available: null, message: "" });
    try {
      const res = await authApi.checkUsername(value);
      setUsernameStatus({
        checking: false,
        available: res.data.available,
        message: res.data.message,
      });
    } catch {
      setUsernameStatus({
        checking: false,
        available: null,
        message: "",
      });
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (username) {
        checkUsername(username);
      } else {
        setUsernameStatus({ checking: false, available: null, message: "" });
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [username, checkUsername]);

  const onSubmit = async (data: RegisterFormData) => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- strip before sending
    const { confirmPassword: _, ...payload } = data;
    await registerUser(payload);
  };

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold">Create an account</CardTitle>
        <CardDescription>
          Get started with Accura&apos;s intelligent AI platform
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="first_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>First Name</FormLabel>
                    <FormControl>
                      <Input placeholder="John" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="last_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Last Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Doe" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input placeholder="johndoe" {...field} />
                      {usernameStatus.checking && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                        </div>
                      )}
                      {!usernameStatus.checking &&
                        usernameStatus.available === true && (
                          <div className="absolute right-3 top-1/2 -translate-y-1/2">
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          </div>
                        )}
                      {!usernameStatus.checking &&
                        usernameStatus.available === false && (
                          <div className="absolute right-3 top-1/2 -translate-y-1/2">
                            <AlertCircle className="h-4 w-4 text-destructive" />
                          </div>
                        )}
                    </div>
                  </FormControl>
                  {usernameStatus.available === false && (
                    <p className="text-sm text-destructive">
                      {usernameStatus.message}
                    </p>
                  )}
                  {usernameStatus.available === true && (
                    <p className="text-sm text-green-500">
                      {usernameStatus.message}
                    </p>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input
                      type="email"
                      placeholder="name@example.com"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Password</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••"
                        {...field}
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                        onClick={() => setShowPassword(!showPassword)}
                        tabIndex={-1}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </FormControl>
                  {/* Password strength indicators */}
                  {password.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {passwordChecks.map((check) => (
                        <div
                          key={check.label}
                          className="flex items-center gap-2 text-xs"
                        >
                          {check.met ? (
                            <Check className="h-3 w-3 text-green-500" />
                          ) : (
                            <X className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span
                            className={
                              check.met
                                ? "text-green-500"
                                : "text-muted-foreground"
                            }
                          >
                            {check.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="confirmPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm Password</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="••••••••"
                        {...field}
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                        onClick={() =>
                          setShowConfirmPassword(!showConfirmPassword)
                        }
                        tabIndex={-1}
                      >
                        {showConfirmPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button
              type="submit"
              className="w-full cursor-pointer"
              disabled={isRegistering}
            >
              {isRegistering && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create Account
            </Button>
          </form>
        </Form>
      </CardContent>
      <CardFooter>
        <p className="text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:underline"
          >
            Sign in
          </Link>
        </p>
      </CardFooter>
    </Card>
  );
}
