"use server";
import { redirect } from "next/navigation";
import { createSession, deleteSession } from "@/lib/session";

export type LoginState = { error: string } | undefined;

export async function login(
  _state: LoginState,
  formData: FormData
): Promise<LoginState> {
  const username = (formData.get("username") as string)?.trim();
  const password = formData.get("password") as string;

  if (
    username !== process.env.RMG_USERNAME ||
    password !== process.env.RMG_PASSWORD
  ) {
    return { error: "Invalid username or password." };
  }

  await createSession(username);
  redirect("/");
}

export async function logout() {
  await deleteSession();
  redirect("/login");
}
