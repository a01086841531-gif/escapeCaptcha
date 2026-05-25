import { getDb } from "@/utils/mongodb";

export async function POST(req) {
  try {
    console.log("✓ API POST 호출됨");
    const body = await req.json();
    console.log("✓ Body 파싱됨:", body);

    const db = await getDb();
    console.log("✓ DB 연결됨");

    const result = await db.collection("captcha_events").insertOne({
      ...body,
      created_at: new Date(),
    });
    console.log("✓ MongoDB 저장 성공:", result.insertedId);

    return Response.json({ success: true });
  } catch (error) {
    console.error("✗ MongoDB 저장 실패:", error);

    return Response.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}