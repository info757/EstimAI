import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import PlanReview from './pages/PlanReview';
import Review from './pages/Review';
import DemoModeBanner from './components/DemoModeBanner';

export default function App() {
  return (
    <BrowserRouter>
      <DemoModeBanner />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/plan" element={<PlanReview />} />
        <Route path="/review" element={<Review />} />
      </Routes>
    </BrowserRouter>
  );
}