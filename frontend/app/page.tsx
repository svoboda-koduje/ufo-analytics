const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

useEffect(() => {
  fetch(`${API_URL}/api/cases/`)
    .then((res) => res.json())
    .then((data) => {
      setCases(data);
      if (data.length > 0) setSelectedCase(data[0]);
      setLoading(false);
    })
    .catch((err) => {
      console.error("Chyba při komunikaci s backendem:", err);
      setLoading(false);
    });
}, []);
