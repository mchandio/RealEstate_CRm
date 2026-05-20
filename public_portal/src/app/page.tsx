"use client";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";

type PublicProperty = {
  id: number;
  title?: string;
  location?: string;
  property_type?: string;
  monthly_rent?: number;
  sale_price?: number;
};

function apiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "");
  }
  if (typeof window === "undefined") {
    return "http://127.0.0.1:6090";
  }
  return `${window.location.protocol}//${window.location.hostname}:6090`;
}

export default function Home() {
  const [properties, setProperties] = useState<PublicProperty[]>([]);
  const [loading, setLoading] = useState(true);

  // Lead form state
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [type, setType] = useState("rent");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch(`${apiBaseUrl()}/api/public/properties`)
      .then(res => res.json())
      .then(data => {
        if (data.ok) {
          setProperties(data.properties);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const submitLead = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStatus("Submitting...");
    try {
      const res = await fetch(`${apiBaseUrl()}/api/public/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, phone, type, message }),
      });
      const data = await res.json();
      if (data.ok) {
        setStatus("Success! We will contact you soon.");
        setName("");
        setPhone("");
        setMessage("");
      } else {
        setStatus("Failed to submit.");
      }
    } catch {
      setStatus("Error submitting form.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <header className="bg-blue-600 text-white py-6 shadow-md">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold">Premium Real Estate</h1>
          <p className="text-blue-100 mt-2">Find your perfect home or investment.</p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Properties Listing */}
        <div className="md:col-span-2">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800">Featured Properties</h2>
          {loading ? (
            <p className="text-gray-500">Loading properties...</p>
          ) : properties.length === 0 ? (
            <p className="text-gray-500">No properties available right now.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {properties.map((p) => (
                <div key={p.id} className="bg-white rounded-lg shadow overflow-hidden border border-gray-200 hover:shadow-lg transition">
                  <div className="h-48 bg-gray-200 flex items-center justify-center text-gray-400">
                    [Property Image]
                  </div>
                  <div className="p-4">
                    <h3 className="text-lg font-bold text-gray-800 truncate">{p.title || "Unnamed Property"}</h3>
                    <p className="text-sm text-gray-500 mt-1">{p.location || "Location not specified"}</p>
                    
                    <div className="mt-4 flex justify-between items-center">
                      <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                        {p.property_type || "Various"}
                      </span>
                      <span className="font-semibold text-green-600">
                        {p.monthly_rent ? `Rs. ${p.monthly_rent}/mo` : p.sale_price ? `Rs. ${p.sale_price}` : "Price on Request"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Lead Capture Form */}
        <div className="md:col-span-1">
          <div className="bg-white rounded-lg shadow-md p-6 sticky top-6 border border-gray-200">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Need help finding a property?</h2>
            <p className="text-sm text-gray-600 mb-6">Drop your details below and our agents will find the perfect property for you.</p>
            
            <form onSubmit={submitLead} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input required type="text" value={name} onChange={e => setName(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800" placeholder="John Doe" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input required type="text" value={phone} onChange={e => setPhone(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800" placeholder="0300..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Looking to</label>
                <select value={type} onChange={e => setType(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800">
                  <option value="rent">Rent</option>
                  <option value="sale">Buy (Sale)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Requirements</label>
                <textarea rows={3} value={message} onChange={e => setMessage(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800" placeholder="E.g. 3 bed flat in Gulshan under 50k..."></textarea>
              </div>
              <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition">
                Send Request
              </button>
              {status && <p className="text-sm text-center mt-2 text-green-600 font-medium">{status}</p>}
            </form>
          </div>
        </div>

      </main>
    </div>
  );
}
