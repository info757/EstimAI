import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import PlanReview from './pages/PlanReview';
import Review from './pages/Review';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/plan" element={<PlanReview />} />
        <Route path="/review" element={<Review />} />
      </Routes>
    </BrowserRouter>
  );
}