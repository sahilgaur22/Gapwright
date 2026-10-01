import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, full_name, role } = body;

    if (!email || !password) {
      return NextResponse.json(
        { detail: "Email and password are required" },
        { status: 400 }
      );
    }

    // 1. Register with backend
    const regRes = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password,
        full_name,
        role: role || "educator",
      }),
    });

    const regData = await regRes.json();
    if (!regRes.ok) {
      return NextResponse.json(
        { detail: regData.detail || "Registration failed" },
        { status: regRes.status }
      );
    }

    // 2. Automatically log in to establish session
    const loginRes = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const loginData = await loginRes.json();
    if (!loginRes.ok) {
      return NextResponse.json({ user: regData }, { status: 201 });
    }

    const response = NextResponse.json(
      {
        user: loginData.user,
        access_token: loginData.access_token,
      },
      { status: 201 }
    );

    // Set secure httpOnly cookie
    response.cookies.set({
      name: "gapwright_session",
      value: loginData.access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24,
    });

    return response;
  } catch (error) {
    return NextResponse.json(
      { detail: `Registration error: ${error instanceof Error ? error.message : "Unknown error"}` },
      { status: 500 }
    );
  }
}
