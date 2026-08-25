import SplatViewer from "./components/SplatViewer";

export default function TestViewer() {
  // Đặt file .ply mẫu vào frontend/public/test.ply rồi trỏ URL vào đó
  const plyUrl = "/test.ply";

  return (
    <div style={{ padding: 24 }}>
      <h1>Test SplatViewer</h1>
      <SplatViewer plyUrl={plyUrl} />
    </div>
  );
}