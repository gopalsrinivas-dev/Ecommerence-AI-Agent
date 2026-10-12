import Orders from "@/features/Orders";
export default async function Page({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = await params;
  return <Orders identity={orderId} />;
}
