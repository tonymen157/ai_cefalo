import { createContext, useContext } from 'react'

const DisclaimerContext = createContext()

export function DisclaimerProvider({ children }) {
  return (
    <DisclaimerContext.Provider value={{}}>
      {children}
    </DisclaimerContext.Provider>
  )
}

export function useDisclaimer() {
  return useContext(DisclaimerContext)
}
