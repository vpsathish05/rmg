import Sidebar from "@/components/layout/sidebar";
import ChatPanel from "@/components/chat-panel";
import DocPanel from "@/components/doc-panel";
import { getSession } from "@/lib/session";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  return (
    <>
      <Sidebar userName={session?.userId ?? "RMG User"} />
      <main className="flex-1 flex flex-col min-h-full overflow-auto">
        {children}
      </main>
      <ChatPanel />
      <DocPanel />
    </>
  );
}
