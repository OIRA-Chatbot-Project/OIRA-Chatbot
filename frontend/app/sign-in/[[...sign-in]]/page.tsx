import { SignIn } from '@clerk/nextjs'

/** Next.js catch-all route that renders the Clerk hosted sign-in widget. */
export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <SignIn />
    </div>
  )
}
