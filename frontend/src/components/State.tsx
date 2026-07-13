import { EmptyState, ErrorPanel, LoadingState } from "@/components/ProductUI";

export function Loading() {
  return <LoadingState />;
}

export function Empty({ text = "暂无数据" }: { text?: string }) {
  return <EmptyState title={text} />;
}

export function ErrorState({ message }: { message: string }) {
  return <ErrorPanel message={message} />;
}
