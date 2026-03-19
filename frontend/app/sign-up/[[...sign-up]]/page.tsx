import { SignUp } from '@clerk/nextjs'

/** Next.js catch-all route that renders the Clerk hosted sign-up widget. */
export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <SignUp />
    </div>
  )
}
